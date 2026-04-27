import os
import queue
import secrets
import threading
import time
import uuid
import logging
from functools import wraps

from flask import (
    Flask, Response, jsonify, request,
    send_from_directory, session, stream_with_context,
)

from config import Config
from models import ScriptStatus, ScriptState, ScriptMetadata
from database import (
    init_db, db_get_all_last_runs, db_insert_run, 
    db_get_run_history
)
from utils import discover_scripts, load_log_file
from runner import ProcessManager
from scheduler import ScriptScheduler

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder="static")
app.secret_key = Config.SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

init_db()

# ── State management ──────────────────────────────────────────────────────────
manager = ProcessManager()
SCRIPTS = discover_scripts()
manager.set_scripts(SCRIPTS)

scheduler = ScriptScheduler(manager)
scheduler.start()
scheduler.sync_schedules(SCRIPTS)

def recover_state():
    last_runs = db_get_all_last_runs()
    recovered = {}
    for key in SCRIPTS:
        row = last_runs.get(key)
        if row:
            status_val = row["status"]
            if status_val == "running":
                from database import db_finish_run
                db_finish_run(row["run_id"], "error", "interrupted", None, "server_restart")
                status_val = "error"
            
            recovered[key] = ScriptState(
                status=ScriptStatus(status_val),
                elapsed=row["elapsed"],
                log_lines=load_log_file(key, row["run_id"]),
                stop_reason=row.get("stop_reason"),
                exit_code=row.get("exit_code"),
            )
        else:
            recovered[key] = ScriptState()
    return recovered

manager.script_state = recover_state()
manager.start_stale_watcher()

_server_start = time.time()

# ── Rate limiter ──────────────────────────────────────────────────────────────
_rate_buckets = {}
_rate_lock = threading.Lock()

def rate_limited(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        ip = request.remote_addr or "unknown"
        now = time.time()
        with _rate_lock:
            buckets = _rate_buckets.get(ip, [])
            buckets = [t for t in buckets if now - t < Config.RATE_WINDOW]
            if len(buckets) >= Config.RATE_MAX:
                return jsonify({"error": "Rate limit exceeded"}), 429
            buckets.append(now)
            _rate_buckets[ip] = buckets
        return f(*args, **kwargs)
    return wrapper

# ── CSRF helpers ──────────────────────────────────────────────────────────────
def get_csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]

def csrf_protected(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("X-CSRF-Token", "")
        expected = session.get("csrf_token", "")
        if not expected or not secrets.compare_digest(token, expected):
            return jsonify({"error": "Invalid or missing CSRF token"}), 403
        return f(*args, **kwargs)
    return wrapper

# ── Security headers ──────────────────────────────────────────────────────────
@app.after_request
def set_security_headers(response):
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; style-src 'self' 'unsafe-inline'; "
        "object-src 'none'; base-uri 'self'; frame-ancestors 'none';"
    )
    return response

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    get_csrf_token()
    response = send_from_directory("static", "index.html")
    response.headers["X-CSRF-Token"] = session["csrf_token"]
    return response

@app.route("/api/csrf-token")
def csrf_token_endpoint():
    return jsonify({"token": get_csrf_token()})

@app.route("/api/scripts")
def get_scripts():
    global SCRIPTS
    current = discover_scripts()
    for key, meta in current.items():
        SCRIPTS[key] = meta
        if key not in manager.script_state:
            manager.script_state[key] = ScriptState()
    
    manager.set_scripts(SCRIPTS)
    
    result = {
        key: state.to_dict(key, SCRIPTS[key])
        for key, state in manager.script_state.items()
        if key in SCRIPTS
    }
    return jsonify(result)

@app.route("/api/run/<key>", methods=["POST"])
@csrf_protected
@rate_limited
def trigger_script(key: str):
    if key not in SCRIPTS:
        return jsonify({"error": "Unknown script"}), 404
    state = manager.script_state[key]
    if state.status == ScriptStatus.RUNNING:
        return jsonify({"error": "Already running"}), 409

    run_id = str(uuid.uuid4())
    state.log_queue = queue.Queue()
    db_insert_run(run_id, key, time.time())
    threading.Thread(target=manager.run_script, args=(key, run_id), daemon=True).start()
    return jsonify({"ok": True, "run_id": run_id})

@app.route("/api/stop/<key>", methods=["POST"])
@csrf_protected
@rate_limited
def stop_script(key: str):
    if key not in SCRIPTS:
        return jsonify({"error": "Unknown script"}), 404
    state = manager.script_state[key]
    if state.status != ScriptStatus.RUNNING:
        return jsonify({"error": "Script is not running"}), 409

    state.stop_flag = True
    if state.proc:
        try:
            state.proc.terminate()
        except OSError:
            pass
    return jsonify({"ok": True})

@app.route("/api/schedule/toggle/<key>", methods=["POST"])
@csrf_protected
@rate_limited
def toggle_schedule(key: str):
    if key not in SCRIPTS:
        return jsonify({"error": "Unknown script"}), 404
    state = manager.script_state[key]
    state.schedule_disabled = not state.schedule_disabled
    return jsonify({"ok": True, "schedule_disabled": state.schedule_disabled})

@app.route("/api/stats/<key>")
def get_stats(key: str):
    from database import db_get_script_stats
    from utils import _KEY_RE
    if not _KEY_RE.match(key):
        return jsonify({"error": "Invalid key"}), 400
    stats = db_get_script_stats(key)
    return jsonify(stats)

@app.route("/api/logs/<key>")
def stream_logs(key: str):
    if key not in SCRIPTS:
        return jsonify({"error": "Unknown script"}), 404

    def generate():
        q = manager.script_state[key].log_queue
        while True:
            try:
                msg = q.get(timeout=30)
                import json
                yield f"data: {json.dumps(msg)}\n\n"
                if msg.get("type") == "done":
                    break
            except queue.Empty:
                yield ": keep-alive\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.route("/api/history/<key>")
def get_history(key: str):
    from utils import _KEY_RE
    if not _KEY_RE.match(key):
        return jsonify({"error": "Invalid key"}), 400
    rows = db_get_run_history(key, limit=20)
    return jsonify(rows)

@app.route("/api/logs/<key>/<run_id>")
def get_run_log(key: str, run_id: str):
    from utils import _KEY_RE, _UUID_RE
    if not _KEY_RE.match(key):
        return jsonify({"error": "Invalid key"}), 400
    if not _UUID_RE.match(run_id):
        return jsonify({"error": "Invalid run_id"}), 400
    lines = load_log_file(key, run_id)
    return jsonify({"run_id": run_id, "lines": lines})

@app.route("/api/health")
def health():
    running = [k for k, s in manager.script_state.items() if s.status == ScriptStatus.RUNNING]
    stale = [k for k, s in manager.script_state.items() if s.stale]
    return jsonify({
        "ok": True,
        "uptime_s": round(time.time() - _server_start),
        "running": running,
        "stale": stale,
        "script_count": len(SCRIPTS),
    })

@app.route("/api/meta/reload", methods=["POST"])
@csrf_protected
def reload_meta():
    global SCRIPTS
    SCRIPTS = discover_scripts()
    manager.set_scripts(SCRIPTS)
    scheduler.sync_schedules(SCRIPTS)
    for key in SCRIPTS:
        if key not in manager.script_state:
            manager.script_state[key] = ScriptState()
    return jsonify({"ok": True, "scripts": list(SCRIPTS.keys())})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)