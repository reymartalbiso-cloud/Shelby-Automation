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


def derive_title_and_body(generated: str, day_of_week: str) -> tuple[str, str]:
    """
    Splits a generated post into a Skool title + body.

    Skool's posts:create requires a title field separately. Shelby's natural
    posts often open with a short headline-style line; if so we lift that as
    the title and keep the rest as the body. If there's no obvious break we
    fall back to the first sentence, then a day-of-week placeholder.
    """
    text = (generated or "").strip()
    if not text:
        return f"{day_of_week} update", ""

    # Preferred shape: short first line, blank or newline, then the rest.
    if "\n" in text:
        first_line, rest = text.split("\n", 1)
        first_line = first_line.strip()
        rest = rest.strip()
        if first_line and len(first_line) <= 100 and rest:
            return first_line, rest

    # Fallback: take the first sentence as the title, keep full text as body.
    for end_char in (".", "!", "?"):
        idx = text.find(end_char)
        if 0 < idx <= 100:
            return text[: idx + 1].strip(), text

    # Last resort: a day-flavoured placeholder so the post still goes out.
    return f"{day_of_week} from Shelby", text


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

    # ── Step 5: Split into title + body, then post via Apify ─
    title, body = derive_title_and_body(post_text, day_of_week)
    logger.info(f"Title: {title!r}")
    logger.info("Posting to Skool community via Apify...")
    success = create_post(title=title, content=body)

    if success:
        logger.info("✅ Daily post published successfully!")
    else:
        logger.error("❌ Failed to publish post to Skool.")
        sys.exit(1)

    logger.info("Workflow 1: Daily Morning Post — Complete")


if __name__ == "__main__":
    run()
