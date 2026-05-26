"""
utils/mock_feed.py
------------------
Persists what would have been posted to Skool during DRY_RUN mode.

When DRY_RUN=true in config.json, every call to create_post / create_reply
in apify_client.py records what would have been sent into mock_feed.json
(project root). The dashboard /feed route then reads that file and renders
it as a Skool-style feed so you can see the posts in a browser.
"""

import json
import logging
import os
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

# Feed file lives at project root next to config.json
FEED_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "mock_feed.json",
)

# Avoid race conditions if two workflows try to append at the same time
_lock = Lock()


def _read_all() -> list[dict]:
    """Reads the mock feed JSON file. Returns empty list if missing/malformed."""
    if not os.path.exists(FEED_PATH):
        return []
    try:
        with open(FEED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        logger.warning(f"mock_feed.json is malformed — treating as empty.")
        return []


def _write_all(entries: list[dict]) -> None:
    """Writes the full feed list back to disk."""
    with open(FEED_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def append_post(body: str, category: str = "general") -> None:
    """Records a top-level post that DRY_RUN would have made."""
    with _lock:
        entries = _read_all()
        entries.append({
            "type": "post",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "body": body,
            "category": category,
        })
        _write_all(entries)
    logger.info(f"[MOCK_FEED] Recorded post ({len(body)} chars) to {FEED_PATH}")


def append_reply(body: str, root_id: str, parent_id: str) -> None:
    """Records a reply that DRY_RUN would have made."""
    with _lock:
        entries = _read_all()
        entries.append({
            "type": "reply",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "body": body,
            "root_id": root_id,
            "parent_id": parent_id,
        })
        _write_all(entries)
    logger.info(f"[MOCK_FEED] Recorded reply to {parent_id} → {FEED_PATH}")


def append_community_comment(
    body: str,
    comment_id: str,
    root_id: str,
    author_name: str,
    author_id: str,
) -> None:
    """
    Records a community member's comment that the system is about to reply to.
    Only used in DRY_RUN — gives the feed page context so you can see what
    Shelby was responding to.
    """
    with _lock:
        entries = _read_all()
        # Skip if we already recorded this exact comment_id (avoid duplicates
        # across repeated scheduler cycles).
        if any(e.get("comment_id") == comment_id and e.get("type") == "community_comment"
               for e in entries):
            return
        entries.append({
            "type": "community_comment",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "body": body,
            "comment_id": comment_id,
            "root_id": root_id,
            "author_name": author_name,
            "author_id": author_id,
        })
        _write_all(entries)
    logger.info(f"[MOCK_FEED] Recorded community comment from {author_name} → {FEED_PATH}")


def read_all() -> list[dict]:
    """Public read accessor (used by the dashboard)."""
    with _lock:
        return _read_all()


def clear() -> int:
    """Clears the feed. Returns how many entries were removed."""
    with _lock:
        existing = _read_all()
        count = len(existing)
        _write_all([])
    logger.info(f"[MOCK_FEED] Cleared {count} entries from {FEED_PATH}")
    return count
