import json
import os
import re
import logging
from pathlib import Path
from config import Config
from models import ScriptMetadata

logger = logging.getLogger(__name__)

_KEY_RE = re.compile(r"^[a-zA-Z0-9_]{1,64}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

def load_script_meta() -> dict:
    if not Config.META_PATH.exists():
        return {}
    try:
        with open(Config.META_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        logger.warning(f"Could not load script_meta.json: {exc}")
    return {}

def extract_description(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().strip("\"'")
                if line and not line.startswith("#"):
                    return line[:80]
    except OSError:
        pass
    return os.path.basename(path)

def discover_scripts() -> dict[str, ScriptMetadata]:
    found = {}
    tasks_dir = Config.BASE_TASKS_DIR
    if not tasks_dir.is_dir():
        logger.warning(f"tasks/ directory not found at {tasks_dir} — no scripts loaded.")
        return found

    script_meta = load_script_meta()

    for filename in sorted(os.listdir(tasks_dir)):
        if not filename.endswith(".py"):
            continue
        key = filename[:-3]
        if not _KEY_RE.match(key):
            logger.info(f"Skipping {filename!r} — invalid key")
            continue
        abs_path = os.path.realpath(tasks_dir / filename)
        if not abs_path.startswith(os.path.realpath(tasks_dir) + os.sep):
            logger.info(f"Skipping {filename!r} — resolves outside tasks/")
            continue

        meta_override = script_meta.get(key, {})
        timeout = int(meta_override.get("timeout", Config.DEFAULT_TIMEOUT))
        
        found[key] = ScriptMetadata(
            name=meta_override.get("display_name", filename),
            file=str(Path("tasks") / filename),
            description=meta_override.get("description") or extract_description(abs_path),
            category=meta_override.get("category", "general"),
            timeout=timeout,
            abs_path=abs_path,
            schedule=meta_override.get("schedule"),
            env=meta_override.get("env", {}),
            args=meta_override.get("args", [])
        )
    return found

def get_log_path(key: str, run_id: str) -> Path:
    d = Config.LOGS_DIR / key
    d.mkdir(exist_ok=True)
    return d / f"{run_id}.log"

def load_log_file(key: str, run_id: str) -> list[str]:
    path = get_log_path(key, run_id)
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return [line.rstrip("\n") for line in f]
    except OSError:
        return []
