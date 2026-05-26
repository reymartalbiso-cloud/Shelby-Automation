"""
test_scheduler.py
-----------------
LOCAL TESTING ONLY — DO NOT DEPLOY THIS TO PRODUCTION.

Runs all three workflows on short intervals so you can watch them fire on
schedule without waiting a full day / hour / week. Intervals are read from
config.json -> TEST_SCHEDULE.

In production, scheduling is handled by cron / Railway / Render — NOT by this
script. The real schedules (7am ET daily, every hour, Monday 8am) are set in
the cron lines documented in README.md.

To start:
    python test_scheduler.py

To stop:
    Press Ctrl+C.

Each script honors SYSTEM_ACTIVE and DRY_RUN from config.json on every run,
so you can pause/resume mid-session by flipping those flags (or using the
dashboard).
"""

import subprocess
import sys
import time
from datetime import datetime, timedelta

# Force UTF-8 on Windows so emoji-containing log lines don't crash on cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from utils.toggle import _read_config


SCRIPTS = [
    ("daily_post.py",     "daily_post_minutes",     3),
    ("comment_reply.py",  "comment_reply_minutes",  5),
    ("weekly_events.py",  "weekly_events_minutes",  10),
]

CHECK_INTERVAL_SECONDS = 5  # how often to check whether anything is due to fire


def run_script(name: str) -> None:
    """Runs a workflow script as a subprocess and streams its output."""
    ts = datetime.now().strftime("%H:%M:%S")
    banner = "▶" * 30
    print(f"\n{banner}")
    print(f"[{ts}] Firing {name}")
    print(banner)
    subprocess.run([sys.executable, name])


def load_intervals() -> dict:
    """Reads the TEST_SCHEDULE block from config.json."""
    config = _read_config()
    sched = config.get("TEST_SCHEDULE", {})
    return {
        script: sched.get(key, default)
        for script, key, default in SCRIPTS
    }


def main() -> None:
    intervals = load_intervals()

    print("=" * 60)
    print("Test scheduler started — local testing only")
    print("=" * 60)
    for script, _, _ in SCRIPTS:
        print(f"  {script:<22} → every {intervals[script]} minute(s)")
    print()
    print("All three will fire immediately at startup, then on interval.")
    print("Press Ctrl+C to stop.")
    print("=" * 60)

    # Schedule each script's next-run time to "now" so they all fire on startup.
    now = datetime.now()
    next_run = {script: now for script, _, _ in SCRIPTS}

    while True:
        now = datetime.now()
        for script, _, _ in SCRIPTS:
            if now >= next_run[script]:
                run_script(script)
                next_run[script] = now + timedelta(minutes=intervals[script])
                nxt = next_run[script].strftime("%H:%M:%S")
                print(f"[scheduler] Next {script} run: {nxt}")

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[scheduler] Stopped by user. All scheduled runs cancelled.")
