"""
comment_reply.py
----------------
Workflow 2: Hourly Comment Reply

Schedule: Every hour (set via cron or Railway/Render scheduler)

What it does:
  1. Checks config.json — if SYSTEM_ACTIVE is false, exits immediately
  2. Fetches the 20 most recent posts from the class-economy Skool group
  3. For each post, fetches all comments
  4. Filters out comments already replied to by Shelby
  5. Filters out comments made by Shelby herself
  6. For each unanswered comment, calls Claude to generate a warm reply
  7. Posts each reply back to Skool via Apify

To run manually:
  python comment_reply.py

Cron schedule (runs every hour):
  0 * * * *  /path/to/venv/bin/python /path/to/ai-shelby/comment_reply.py
"""

import logging
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 on Windows so emoji-containing log lines don't crash on cp1252.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Load shared modules ──────────────────────────────────────
from shelby_prompt import SHELBY_SYSTEM_PROMPT
from utils.toggle import is_system_active, is_dry_run
from utils.claude_client import generate_content
from utils.apify_client import list_posts, list_comments, create_reply
from utils.mock_feed import append_community_comment

# ── Logging Setup ────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("comment_reply")

# ── Delay between replies (be kind to APIs) ──────────────────
REPLY_DELAY_SECONDS = 3


def get_shelby_user_id() -> str:
    """
    Reads Shelby's Skool user ID from environment variables.
    This ID is used to detect which comments Shelby already replied to.
    """
    user_id = os.getenv("SHELBY_USER_ID")
    if not user_id or user_id == "shelby_skool_user_id_here":
        raise EnvironmentError(
            "SHELBY_USER_ID is not set in .env. "
            "Run Apify with action 'posts:list' and find Shelby's 'createdBy.id' value."
        )
    return user_id


def has_shelby_replied(comment: dict, shelby_user_id: str) -> bool:
    """
    Checks if Shelby has already replied to a given comment.

    Args:
        comment:        The comment object from Apify.
        shelby_user_id: Shelby's Skool user ID.

    Returns:
        True if Shelby already replied, False if she hasn't.
    """
    replies = comment.get("replies", [])
    if not replies:
        return False
    return any(
        reply.get("createdBy", {}).get("id") == shelby_user_id
        for reply in replies
    )


def is_shelby_comment(comment: dict, shelby_user_id: str) -> bool:
    """Returns True if the comment was written by Shelby herself."""
    return comment.get("createdBy", {}).get("id") == shelby_user_id


def build_reply_prompt(comment_body: str) -> str:
    """Builds the Claude user message for generating a reply."""
    return (
        f"A teacher in my Class Economy community just posted this comment: "
        f"'{comment_body}'. "
        f"Write a warm, helpful reply as Shelby. "
        f"Keep it under 80 words. Sound natural, like a text from a fellow teacher. "
        f"1 emoji max."
    )


def process_post(post: dict, shelby_user_id: str) -> tuple[int, int]:
    """
    Processes a single post: finds unanswered comments and replies to them.

    Args:
        post:           A post object from Apify.
        shelby_user_id: Shelby's Skool user ID.

    Returns:
        Tuple of (replies_posted, replies_skipped)
    """
    post_id = post.get("id")
    post_preview = (post.get("body", "") or "")[:60]
    logger.info(f"Processing post [{post_id}]: {post_preview!r}...")

    # Fetch comments for this post
    comments = list_comments(post_id)
    if not comments:
        logger.info(f"  No comments found for post [{post_id}]")
        return 0, 0

    # Filter to unanswered comments from other users
    unanswered = [
        c for c in comments
        if not is_shelby_comment(c, shelby_user_id)
        and not has_shelby_replied(c, shelby_user_id)
    ]

    logger.info(
        f"  {len(comments)} total comments, {len(unanswered)} need a reply"
    )

    replies_posted = 0
    replies_skipped = 0

    for comment in unanswered:
        comment_id = comment.get("id")
        comment_body = comment.get("body", "").strip()

        if not comment_body:
            logger.warning(f"  Skipping comment [{comment_id}] — empty body")
            replies_skipped += 1
            continue

        # Determine the root post ID for threading the reply correctly
        root_id = comment.get("rootId") or post_id

        # In dry-run mode, record the community comment we're about to reply
        # to on the mock feed — gives the feed page context.
        if is_dry_run():
            author = comment.get("createdBy", {})
            append_community_comment(
                body=comment_body,
                comment_id=comment_id,
                root_id=root_id,
                author_name=author.get("name", "Unknown teacher"),
                author_id=author.get("id", "unknown"),
            )

        # Generate reply with Claude
        prompt = build_reply_prompt(comment_body)
        reply_text = generate_content(
            system_prompt=SHELBY_SYSTEM_PROMPT,
            user_message=prompt,
            max_tokens=200,
        )

        if not reply_text:
            logger.error(f"  Failed to generate reply for comment [{comment_id}]. Skipping.")
            replies_skipped += 1
            continue

        logger.info(f"  Replying to comment [{comment_id}]: {reply_text[:60]!r}...")

        # Post the reply
        success = create_reply(
            body=reply_text,
            root_id=root_id,
            parent_id=comment_id,
        )

        if success:
            logger.info(f"  ✅ Reply posted to comment [{comment_id}]")
            replies_posted += 1
        else:
            logger.error(f"  ❌ Failed to post reply to comment [{comment_id}]")
            replies_skipped += 1

        # Small delay between replies to avoid hammering the API
        time.sleep(REPLY_DELAY_SECONDS)

    return replies_posted, replies_skipped


def run():
    """Main entry point for Workflow 2: Hourly Comment Reply."""

    logger.info("=" * 60)
    logger.info("Workflow 2: Hourly Comment Reply — Starting")
    logger.info("=" * 60)

    # ── Step 1: Check toggle ──────────────────────────────────
    if not is_system_active():
        logger.info("System is paused. Exiting without replying.")
        sys.exit(0)

    # ── Step 2: Get Shelby's user ID ─────────────────────────
    try:
        shelby_user_id = get_shelby_user_id()
        logger.info(f"Shelby's user ID loaded: {shelby_user_id}")
    except EnvironmentError as e:
        logger.error(str(e))
        sys.exit(1)

    # ── Step 3: Fetch recent posts ────────────────────────────
    logger.info("Fetching 20 most recent posts from Skool...")
    posts = list_posts(limit=20)

    if not posts:
        logger.warning("No posts returned from Skool. Nothing to process.")
        sys.exit(0)

    logger.info(f"Fetched {len(posts)} posts. Processing each for unanswered comments...")

    # ── Step 4–7: Process each post ───────────────────────────
    total_posted = 0
    total_skipped = 0

    for post in posts:
        posted, skipped = process_post(post, shelby_user_id)
        total_posted += posted
        total_skipped += skipped

    # ── Summary ───────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(
        f"Workflow 2 Complete — "
        f"✅ {total_posted} replies posted, "
        f"⚠️  {total_skipped} skipped"
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
