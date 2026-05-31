"""
scheduler.py
------------
In-process scheduler for AI Shelby (the "single combined service" model).

This replaces platform cron. It fires the three workflow scripts on their real
schedules, in America/New_York time — so daylight-saving is handled
automatically and there are no twice-a-year cron edits to make.

Schedules:
  daily_post.py     — every day at 7:00 AM Eastern
  comment_reply.py  — every hour, on the hour
  weekly_events.py  — every Monday at 8:00 AM Eastern

Each workflow runs as its own subprocess — exactly as it would under cron — so
a crash (or a sys.exit) inside one job can never take down the scheduler. Every
script still checks SYSTEM_ACTIVE on its first line, so the dashboard toggle
pauses/resumes everything without the scheduler needing to know anything.

Two ways to run:
  • Combined service (recommended): dashboard/app.py imports
    start_background_scheduler() and runs it alongside Flask in one process.
  • Standalone: `python scheduler.py` runs a blocking scheduler on its own.
"""

import logging
import os
import subprocess
import sys

# Force UTF-8 on Windows so emoji-containing log lines don't crash on cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Project root = the folder this file lives in (where the workflow scripts are).
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# All schedules are expressed in Shelby's timezone. APScheduler converts to the
# server clock for us, including DST transitions.
TIMEZONE = "America/New_York"

# Max seconds a single workflow run may take before we abandon it. Stops a hung
# job (e.g. a stuck API call) from blocking the next cycle forever.
JOB_TIMEOUT_SECONDS = 540

logger = logging.getLogger("scheduler")


def run_workflow(script_name: str) -> None:
    """Runs one workflow script as a subprocess, exactly as cron would."""
    script_path = os.path.join(PROJECT_ROOT, script_name)
    logger.info(f"Firing {script_name} ...")
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            cwd=PROJECT_ROOT,
            timeout=JOB_TIMEOUT_SECONDS,
        )
        logger.info(f"{script_name} finished (exit code {result.returncode})")
    except subprocess.TimeoutExpired:
        logger.error(f"{script_name} timed out after {JOB_TIMEOUT_SECONDS}s — abandoned")
    except Exception as e:
        logger.error(f"{script_name} failed to launch: {e}")


def _add_jobs(scheduler) -> None:
    """Registers the three workflow schedules (all in Eastern Time)."""
    # Daily morning post — 7:00 AM ET, every day
    scheduler.add_job(
        run_workflow, args=["daily_post.py"],
        trigger=CronTrigger(hour=7, minute=0, timezone=TIMEZONE),
        id="daily_post", name="Daily Morning Post",
        max_instances=1, coalesce=True, misfire_grace_time=3600,
    )
    # Hourly comment reply — top of every hour
    scheduler.add_job(
        run_workflow, args=["comment_reply.py"],
        trigger=CronTrigger(minute=0, timezone=TIMEZONE),
        id="comment_reply", name="Hourly Comment Reply",
        max_instances=1, coalesce=True, misfire_grace_time=600,
    )
    # Weekly events — Monday 8:00 AM ET
    scheduler.add_job(
        run_workflow, args=["weekly_events.py"],
        trigger=CronTrigger(day_of_week="mon", hour=8, minute=0, timezone=TIMEZONE),
        id="weekly_events", name="Weekly Event Generator",
        max_instances=1, coalesce=True, misfire_grace_time=3600,
    )


def _log_jobs(scheduler) -> None:
    """Logs each registered job and its next fire time."""
    for job in scheduler.get_jobs():
        logger.info(f"  • {job.name}: next run {job.next_run_time}")


def start_background_scheduler() -> BackgroundScheduler:
    """
    Creates and starts a non-blocking BackgroundScheduler.

    Used by the combined service so the Flask dashboard keeps serving requests
    while the scheduler fires jobs on background threads. Returns the scheduler
    so the caller can hold a reference (or shut it down).
    """
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    _add_jobs(scheduler)
    scheduler.start()
    logger.info("Background scheduler started. Jobs:")
    _log_jobs(scheduler)
    return scheduler


def main() -> None:
    """Standalone blocking scheduler — an alternative to the combined service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    _add_jobs(scheduler)
    logger.info("Starting blocking scheduler (Ctrl+C to stop). Jobs:")
    _log_jobs(scheduler)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
