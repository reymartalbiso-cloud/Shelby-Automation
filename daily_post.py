"""
daily_post.py
-------------
Workflow 1: Daily Morning Post

Schedule: Every day at 7:00 AM Eastern Time (set via cron or Railway/Render scheduler)

What it does:
  1. Checks config.json — if SYSTEM_ACTIVE is false, exits immediately
  2. Determines the current day of the week (in Eastern Time)
  3. Selects the matching content type for that day
  4. Calls Claude API to generate a post in Shelby's voice
  5. Posts the content to the class-economy Skool group via Apify

To run manually:
  python daily_post.py

Cron schedule (Eastern Time — adjust for your server timezone):
  0 7 * * *  /path/to/venv/bin/python /path/to/ai-shelby/daily_post.py
"""

import logging
import sys
from datetime import datetime

import pytz

# Force UTF-8 on Windows so emoji-containing log lines don't crash on cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Load shared modules ──────────────────────────────────────
from shelby_prompt import SHELBY_SYSTEM_PROMPT, DAY_CONTENT_MAP
from utils.toggle import is_system_active
from utils.claude_client import generate_content
from utils.apify_client import create_post

# ── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("daily_post")


def get_day_of_week_eastern() -> str:
    """Returns the current day of week in Eastern Time (e.g. 'Monday')."""
    eastern = pytz.timezone("America/New_York")
    now_et = datetime.now(eastern)
    day = now_et.strftime("%A")
    logger.info(f"Current day in Eastern Time: {day} ({now_et.strftime('%Y-%m-%d %H:%M %Z')})")
    return day


def build_user_message(day_of_week: str, content_info: dict) -> str:
    """Builds the Claude user message prompt for the given day."""
    return (
        f"Write a daily community post for teachers in the Class Economy community. "
        f"Today is {day_of_week}. Make it engaging, warm, and actionable. "
        f"Content type for today: {content_info['type']}. "
        f"Focus: {content_info['description']} "
        f"Keep it under 200 words. Use 1-2 emojis naturally. Do not use hashtags."
    )


def run():
    """Main entry point for Workflow 1: Daily Morning Post."""

    logger.info("=" * 60)
    logger.info("Workflow 1: Daily Morning Post — Starting")
    logger.info("=" * 60)

    # ── Step 1: Check toggle ──────────────────────────────────
    if not is_system_active():
        logger.info("System is paused. Exiting without posting.")
        sys.exit(0)

    # ── Step 2: Get day of week ───────────────────────────────
    day_of_week = get_day_of_week_eastern()

    # ── Step 3: Get content type for today ───────────────────
    content_info = DAY_CONTENT_MAP.get(day_of_week)
    if not content_info:
        logger.error(f"No content type found for day: {day_of_week}")
        sys.exit(1)

    logger.info(f"Today's content type: {content_info['type']}")

    # ── Step 4: Generate post with Claude ────────────────────
    user_message = build_user_message(day_of_week, content_info)
    logger.info(f"Calling Claude API to generate post...")

    post_text = generate_content(
        system_prompt=SHELBY_SYSTEM_PROMPT,
        user_message=user_message,
        max_tokens=500,
    )

    if not post_text:
        logger.error("Failed to generate post content. Exiting.")
        sys.exit(1)

    logger.info(f"Generated post ({len(post_text)} chars):\n{'-'*40}\n{post_text}\n{'-'*40}")

    # ── Step 5: Post to Skool via Apify ──────────────────────
    logger.info("Posting to Skool community via Apify...")
    success = create_post(body=post_text, category="general")

    if success:
        logger.info("✅ Daily post published successfully!")
    else:
        logger.error("❌ Failed to publish post to Skool.")
        sys.exit(1)

    logger.info("Workflow 1: Daily Morning Post — Complete")


if __name__ == "__main__":
    run()
