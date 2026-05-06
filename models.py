from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, List
import queue
import subprocess
import time

class ScriptStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    STOPPED = "stopped"
    SCHEDULED = "scheduled"

@dataclass
class ScriptMetadata:
    name: str
    file: str
    description: str
    category: str
    timeout: int
    abs_path: str
    schedule: Optional[str] = None  # cron expression or "every X minutes"
    venv_path: Optional[str] = None
    webhook_url: Optional[str] = None
    env: dict[str, str] = field(default_factory=dict)
    args: list[str] = field(default_factory=list)

@dataclass
class ScriptState:
    status: ScriptStatus = ScriptStatus.IDLE
    elapsed: Optional[str] = None
    log_queue: queue.Queue = field(default_factory=queue.Queue)
    started_at: Optional[float] = None
    run_id: Optional[str] = None
    proc: Optional[subprocess.Popen] = None
    stop_flag: bool = False
    stale: bool = False
    log_lines: List[str] = field(default_factory=list)
    stop_reason: Optional[str] = None
    exit_code: Optional[int] = None
    schedule_disabled: bool = False
    cpu_usage: float = 0.0
    mem_usage: float = 0.0

    def to_dict(self, key: str, meta: ScriptMetadata) -> dict:
        return {
            "id":          key,
            "name":        meta.name,
            "description": meta.description,
            "category":    meta.category,
            "timeout":     meta.timeout,
            "status":      self.status.value,
            "elapsed":     str(self.elapsed) if self.elapsed else None,
            "run_id":      self.run_id,
            "log_lines":   self.log_lines,
            "stale":       self.stale,
            "stop_reason": self.stop_reason,
            "exit_code":   self.exit_code,
            "schedule":    meta.schedule,
            "schedule_disabled": self.schedule_disabled,
            "cpu_usage": self.cpu_usage,
            "mem_usage": self.mem_usage,
            "env":         meta.env,
            "args":        meta.args,
            "venv_path":   meta.venv_path,
            "webhook_url": meta.webhook_url,
        }
