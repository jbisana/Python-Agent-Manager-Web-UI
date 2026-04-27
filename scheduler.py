import logging
import uuid
import threading
import time
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from models import ScriptMetadata, ScriptStatus
from database import db_insert_run

logger = logging.getLogger(__name__)

class ScriptScheduler:
    def __init__(self, manager):
        self.manager = manager
        self.scheduler = BackgroundScheduler()
        self.jobs = {}

    def start(self):
        self.scheduler.start()
        logger.info("Scheduler started")

    def sync_schedules(self, scripts: dict[str, ScriptMetadata]):
        """Update scheduled jobs based on current metadata."""
        current_keys = set(scripts.keys())
        
        # Remove jobs for scripts that no longer exist or have no schedule
        for key in list(self.jobs.keys()):
            if key not in current_keys or not scripts[key].schedule:
                self.remove_job(key)

        # Add or update jobs
        for key, meta in scripts.items():
            if meta.schedule:
                self.add_or_update_job(key, meta)

    def add_or_update_job(self, key: str, meta: ScriptMetadata):
        schedule_str = meta.schedule
        try:
            trigger = self._parse_schedule(schedule_str)
            if not trigger:
                return

            if key in self.jobs:
                self.scheduler.reschedule_job(self.jobs[key], trigger=trigger)
                logger.info(f"Rescheduled job for {key}: {schedule_str}")
            else:
                job = self.scheduler.add_job(
                    self._trigger_run,
                    trigger=trigger,
                    args=[key],
                    id=key,
                    replace_existing=True
                )
                self.jobs[key] = job.id
                logger.info(f"Scheduled job for {key}: {schedule_str}")
        except Exception as e:
            logger.error(f"Failed to schedule job for {key} ({schedule_str}): {e}")

    def remove_job(self, key: str):
        if key in self.jobs:
            try:
                self.scheduler.remove_job(self.jobs[key])
                logger.info(f"Removed scheduled job for {key}")
            except Exception:
                pass
            del self.jobs[key]

    def _parse_schedule(self, s: str):
        if s.startswith("interval:"):
            # Format: interval:5 (minutes)
            try:
                mins = int(s.split(":")[1])
                return IntervalTrigger(minutes=mins)
            except (ValueError, IndexError):
                return None
        elif s.startswith("cron:"):
            # Format: cron:0 0 * * *
            try:
                expr = s.split(":", 1)[1]
                return CronTrigger.from_crontab(expr)
            except Exception:
                return None
        return None

    def _trigger_run(self, key: str):
        """Callback for scheduled job."""
        state = self.manager.script_state.get(key)
        if not state:
            return

        if state.schedule_disabled:
            logger.info(f"Scheduled run for {key} skipped: schedule is disabled")
            return

        if state.status == ScriptStatus.RUNNING:
            logger.warning(f"Scheduled run for {key} skipped: already running")
            return

        run_id = str(uuid.uuid4())
        logger.info(f"Triggering scheduled run for {key} (run_id: {run_id})")
        
        # We need to handle the DB insert and thread start similarly to the API
        # Since the scheduler runs in its own thread, we can call run_script directly or via a thread
        db_insert_run(run_id, key, time.time())
        threading.Thread(target=self.manager.run_script, args=(key, run_id), daemon=True).start()
