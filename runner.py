import subprocess
import threading
import time
import os
import queue
import logging
import psutil
import requests
from typing import Dict, Optional
from config import Config
from models import ScriptState, ScriptStatus, ScriptMetadata
from database import db_finish_run
from utils import get_log_path

logger = logging.getLogger(__name__)

class ProcessManager:
    def __init__(self):
        self.script_state: Dict[str, ScriptState] = {}
        self.scripts: Dict[str, ScriptMetadata] = {}

    def set_scripts(self, scripts: Dict[str, ScriptMetadata]):
        self.scripts = scripts

    def kill_proc(self, proc: subprocess.Popen, grace: int = Config.KILL_GRACE):
        if proc is None:
            return
        try:
            proc.terminate()
        except OSError:
            return
        try:
            proc.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass

    def run_script(self, key: str, run_id: str):
        state = self.script_state[key]
        state.status = ScriptStatus.RUNNING
        state.started_at = time.time()
        state.elapsed = None
        state.run_id = run_id
        state.log_lines = []
        state.stop_flag = False
        state.stale = False
        state.stop_reason = None
        state.exit_code = None
        q = state.log_queue

        meta = self.scripts[key]
        full_path = meta.abs_path
        timeout_secs = meta.timeout
        log_file_path = get_log_path(key, run_id)

        # Merge environment variables
        env = os.environ.copy()
        if meta.env:
            env.update(meta.env)

        # Determine python interpreter
        python_exe = "python"
        if meta.venv_path:
            # Check for common venv executable locations (Windows vs Unix)
            potential_exes = [
                os.path.join(meta.venv_path, "Scripts", "python.exe"),
                os.path.join(meta.venv_path, "bin", "python"),
            ]
            for exe in potential_exes:
                if os.path.exists(exe):
                    python_exe = exe
                    break

        # Prepare command
        cmd = [python_exe, "-u", full_path]
        if meta.args:
            cmd.extend(meta.args)

        exit_code = None
        stop_reason = None

        try:
            with open(log_file_path, "w", encoding="utf-8") as log_fh:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env,
                )
                state.proc = proc

                def timeout_watchdog():
                    if timeout_secs and timeout_secs > 0:
                        time.sleep(timeout_secs)
                        if state.status == ScriptStatus.RUNNING and state.proc is proc:
                            msg = f"[WARN] Timeout after {timeout_secs}s — killing process"
                            q.put({"type": "log", "text": msg})
                            log_fh.write(msg + "\n")
                            log_fh.flush()
                            state.stop_reason = "timeout"
                            self.kill_proc(proc)

                if timeout_secs and timeout_secs > 0:
                    threading.Thread(target=timeout_watchdog, daemon=True).start()

                def resource_monitor():
                    try:
                        p = psutil.Process(proc.pid)
                        while proc.poll() is None:
                            try:
                                cpu = p.cpu_percent(interval=1)
                                mem = p.memory_info().rss / (1024 * 1024) # MB
                                state.cpu_usage = cpu
                                state.mem_usage = round(mem, 1)
                                q.put({"type": "stats", "cpu": cpu, "mem": state.mem_usage})
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                break
                    except Exception:
                        pass
                    state.cpu_usage = 0.0
                    state.mem_usage = 0.0

                threading.Thread(target=resource_monitor, daemon=True).start()

                try:
                    for raw_line in proc.stdout:
                        line = raw_line.rstrip()[:2048]
                        log_fh.write(line + "\n")
                        log_fh.flush()
                        state.log_lines.append(line)
                        q.put({"type": "log", "text": line})

                        if state.stop_flag:
                            msg = "[INFO] Stop requested — killing process"
                            q.put({"type": "log", "text": msg})
                            log_fh.write(msg + "\n")
                            log_fh.flush()
                            state.stop_reason = "user_stop"
                            self.kill_proc(proc)
                            break
                finally:
                    if proc.stdout:
                        proc.stdout.close()
                    proc.wait()
                exit_code = proc.returncode
                elapsed = round(time.time() - state.started_at, 1)
                state.elapsed = f"{elapsed}s"
                state.exit_code = exit_code

                if state.stop_reason == "user_stop":
                    state.status = ScriptStatus.STOPPED
                elif state.stop_reason == "timeout":
                    state.status = ScriptStatus.ERROR
                else:
                    state.status = ScriptStatus.DONE if exit_code == 0 else ScriptStatus.ERROR

        except FileNotFoundError:
            msg = f"[ERROR] Script not found: {full_path}"
            q.put({"type": "log", "text": msg})
            state.status = ScriptStatus.ERROR
            state.stop_reason = "not_found"
        except Exception as exc:
            msg = f"[ERROR] {exc}"
            logger.exception("Error running script %s", key)
            q.put({"type": "log", "text": msg})
            state.status = ScriptStatus.ERROR
        finally:
            state.proc = None
            elapsed_raw = round(time.time() - (state.started_at or time.time()), 1)
            state.elapsed = state.elapsed or f"{elapsed_raw}s"
            stop_reason = state.stop_reason
            db_finish_run(run_id, state.status.value, state.elapsed, exit_code, stop_reason)
            
            # Basic notification placeholder
            if state.status == ScriptStatus.ERROR:
                logger.error(f"Script {key} failed (run_id: {run_id})")
            elif state.status == ScriptStatus.DONE:
                logger.info(f"Script {key} completed successfully")

            q.put({
                "type":        "done",
                "status":      state.status.value,
                "elapsed":     state.elapsed,
                "exit_code":   exit_code,
                "stop_reason": stop_reason,
            })

            # Webhook trigger
            if meta.webhook_url:
                try:
                    payload = {
                        "script": key,
                        "status": state.status.value,
                        "elapsed": state.elapsed,
                        "exit_code": exit_code,
                        "stop_reason": stop_reason,
                        "run_id": run_id
                    }
                    threading.Thread(target=lambda: requests.post(meta.webhook_url, json=payload, timeout=10), daemon=True).start()
                except Exception as e:
                    logger.error(f"Failed to trigger webhook for {key}: {e}")

    def stale_watcher(self):
        while True:
            time.sleep(60)
            for key, state in self.script_state.items():
                if state.status == ScriptStatus.RUNNING and state.started_at:
                    age = time.time() - state.started_at
                    state.stale = age > Config.STALE_THRESHOLD
                else:
                    state.stale = False

    def start_stale_watcher(self):
        threading.Thread(target=self.stale_watcher, daemon=True).start()
