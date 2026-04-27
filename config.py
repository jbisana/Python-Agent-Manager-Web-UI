import os
import secrets
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    BASE_TASKS_DIR = BASE_DIR / "tasks"
    LOGS_DIR = BASE_DIR / "run_logs"
    DB_PATH = BASE_DIR / "history.db"
    META_PATH = BASE_DIR / "script_meta.json"

    # Security
    SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    
    # Run config
    DEFAULT_TIMEOUT = int(os.environ.get("SCRIPT_TIMEOUT", 3600))
    STALE_THRESHOLD = int(os.environ.get("STALE_THRESHOLD", 1800))
    KILL_GRACE = 5
    
    # Rate limiting
    RATE_WINDOW = 60
    RATE_MAX = 10

    @classmethod
    def ensure_dirs(cls):
        cls.LOGS_DIR.mkdir(exist_ok=True)

Config.ensure_dirs()
