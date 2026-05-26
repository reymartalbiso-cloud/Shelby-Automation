"""
weekly_events.py
----------------
Workflow 3: Weekly Event Generator

Schedule: Every Monday at 8:00 AM Eastern Time (set via cron or Railway/Render scheduler)

What it does:
  1. Checks config.json — if SYSTEM_ACTIVE is false, exits immediately
  2. Calls Claude API to generate 4 community event ideas for the week (as JSON)
  3. Parses the JSON response (stripping any markdown code fences)
  4. Posts each event as a separate community post in Skool via Apify

To run manually:
  python weekly_events.py

Cron schedule (Monday 8:00 AM Eastern Time):
  0 8 * * 1  /path/to/venv/bin/python /path/to/ai-shelby/weekly_events.py
"""

import json
import logging
import re
import sys
import time

# Force UTF-8 on Windows so emoji-containing log lines don't crash on cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Load shared modules ──────────────────────────────────────
from shelby_prompt import SHELBY_SYSTEM_PROMPT
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
logger = logging.getLogger("weekly_events")

# ── Delay between event posts (be kind to APIs) ──────────────
POST_DELAY_SECONDS = 5

# ── Claude prompt for event generation ───────────────────────
EVENTS_USER_MESSAGE = (
    "Generate 4 community event ideas for this week in the Class Economy teacher community. "
    "Events should be interactive challenges, Q&A sessions, or shared wins. "
    "Format as JSON array: [{\"title\": \"\", \"description\": \"\", \"day_of_week\": \"\", \"event_type\": \"\"}]. "
    "Event types must be one of: challenge, livestream, Q&A, share-your-win. "
    "Keep titles under 10 words. "
    "Make the descriptions warm and exciting — something teachers will actually want to participate in. "
    "Return ONLY the JSON array, no extra text."
)


def strip_code_fences(text: str) -> str:
    """
    Strips markdown code fences from Claude's response.
    Claude sometimes wraps JSON in ```json ... ``` blocks.
    This removes those wrappers so we can parse cleanly.
    """
    # Remove ```json ... ``` or ``` ... ``` wrappers
    cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip())
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())
    return cleaned.strip()


def parse_events(raw_text: str) -> list[dict]:
    """
    Parses Claude's JSON response into a list of event dicts.

    Args:
        raw_text: Raw text from Claude (may have code fences).

    Returns:
        List of event dicts, or empty list if parsing fails.
    """
    cleaned = strip_code_fences(raw_text)
    try:
        events = json.loads(cleaned)
        if not isinstance(events, list):
            logger.error("Claude returned JSON but it's not an array.")
            return []
        logger.info(f"Successfully parsed {len(events)} event(s) from Claude.")
        return events
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse events JSON: {e}")
        logger.error(f"Raw Claude response was:\n{raw_text}")
        return []


def format_event_post(event: dict, index: int) -> str:
    """
    Formats a single event dict into a readable Skool post body.

    Args:
        event: Dict with keys: title, description, day_of_week, event_type
        index: Position in the list (1-4) for display

    Returns:
        Formatted post text string.
    """
    title = event.get("title", "This Week's Event").strip()
    description = event.get("description", "").strip()
    day = event.get("day_of_week", "").strip()
    event_type = event.get("event_type", "").strip()

    # Build the post body
    lines = [f"📅 Week Event #{index}: {title}"]

    if event_type:
        lines.append(f"Type: {event_type.replace('-', ' ').title()}")

    if day:
        lines.append(f"When: {day}")

    lines.append("")  # blank line

    if description:
        lines.append(description)

    return "\n".join(lines)


def run():
    """Main entry point for Workflow 3: Weekly Event Generator."""

    logger.info("=" * 60)
    logger.info("Workflow 3: Weekly Event Generator — Starting")
    logger.info("=" * 60)

    # ── Step 1: Check toggle ──────────────────────────────────
    if not is_system_active():
        logger.info("System is paused. Exiting without generating events.")
        sys.exit(0)

    # ── Step 2: Generate 4 event ideas with Claude ────────────
    logger.info("Calling Claude API to generate 4 event ideas...")
    raw_response = generate_content(
        system_prompt=SHELBY_SYSTEM_PROMPT,
        user_message=EVENTS_USER_MESSAGE,
        max_tokens=600,
    )

    if not raw_response:
        logger.error("Failed to generate events from Claude. Exiting.")
        sys.exit(1)

    logger.info(f"Claude raw response:\n{raw_response}")

    # ── Step 3: Parse the JSON response ──────────────────────
    events = parse_events(raw_response)
    if not events:
        logger.error("Could not parse any events from Claude's response. Exiting.")
        sys.exit(1)

    if len(events) < 4:
        logger.warning(f"Expected 4 events but only got {len(events)}. Proceeding with what we have.")

    # ── Step 4: Post each event to Skool ─────────────────────
    logger.info(f"Posting {len(events)} event announcement(s) to Skool...")
    posted_count = 0
    failed_count = 0

    for i, event in enumerate(events, start=1):
        post_body = format_event_post(event, i)
        logger.info(f"Posting event {i}/{len(events)}: {event.get('title', 'Untitled')}")
        logger.debug(f"Post body:\n{post_body}")

        success = create_post(body=post_body, category="general")

        if success:
            logger.info(f"  ✅ Event {i} posted successfully!")
            posted_count += 1
        else:
            logger.error(f"  ❌ Failed to post event {i}.")
            failed_count += 1

        # Delay between posts
        if i < len(events):
            time.sleep(POST_DELAY_SECONDS)

    # ── Summary ───────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(
        f"Workflow 3 Complete — "
        f"✅ {posted_count} events posted, "
        f"❌ {failed_count} failed"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
