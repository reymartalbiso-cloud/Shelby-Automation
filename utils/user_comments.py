"""
utils/user_comments.py
----------------------
Stores comments the user submits via the /feed page's comment form.

These comments are picked up by mock_list_comments() in mock_fixtures.py
so the regular comment_reply.py workflow naturally finds and replies to
them — exactly the way the production system will work against real Skool.

Each comment has a `replied` flag. Once create_reply() runs against it,
the flag flips to true and future cycles skip it (no duplicate replies).
"""

import json
import logging
import os
import uuid
from datetime import datetime
from threading import Lock

logger = logging.getLogger(__name__)

USER_COMMENTS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "user_comments.json",
)

_lock = Lock()


def _read_all() -> list[dict]:
    """Reads the user comments file. Returns empty list if missing/malformed."""
    if not os.path.exists(USER_COMMENTS_PATH):
        return []
    try:
        with open(USER_COMMENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        logger.warning("user_comments.json is malformed — treating as empty.")
        return []


def _write_all(entries: list[dict]) -> None:
    """Writes the full list back to disk."""
    with open(USER_COMMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)


def add(body: str, post_id: str, author_name: str) -> dict:
    """
    Stores a new user-submitted comment. Returns the persisted entry
    (including the generated id) so the caller can mirror it onto the
    visible mock feed.
    """
    entry = {
        "id": f"user_{uuid.uuid4().hex[:10]}",
        "post_id": post_id,
        "body": body.strip(),
        "author_name": author_name.strip() or "Anonymous teacher",
        "author_id": f"user_{author_name.lower().replace(' ', '_') or 'anon'}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "replied": False,
    }
    with _lock:
        entries = _read_all()
        entries.append(entry)
        _write_all(entries)
    logger.info(f"[USER_COMMENT] Stored {entry['id']} on post {post_id} from {author_name}")
    return entry


def get_unreplied_for_post(post_id: str) -> list[dict]:
    """
    Returns user comments for a given post that haven't been replied to yet.
    Shape mirrors the Apify Skool comment format so mock_list_comments() can
    splice them in directly alongside the rotating mock comments.
    """
    with _lock:
        entries = _read_all()

    comments = []
    for e in entries:
        if e.get("post_id") != post_id:
            continue
        if e.get("replied"):
            continue
        comments.append({
            "id": e["id"],
            "rootId": post_id,
            "body": e["body"],
            "createdBy": {"id": e["author_id"], "name": e["author_name"]},
            "replies": [],
        })
    return comments


def mark_replied(comment_id: str) -> bool:
    """
    Flips the `replied` flag for a given user comment id. Called by
    apify_client.create_reply() in DRY_RUN mode after a reply is posted
    so the same comment isn't picked up again next cycle.

    Returns True if a matching comment was found and updated.
    """
    if not comment_id or not comment_id.startswith("user_"):
        return False

    with _lock:
        entries = _read_all()
        for e in entries:
            if e.get("id") == comment_id and not e.get("replied"):
                e["replied"] = True
                e["replied_at"] = datetime.now().isoformat(timespec="seconds")
                _write_all(entries)
                logger.info(f"[USER_COMMENT] Marked {comment_id} as replied")
                return True
    return False


def read_all() -> list[dict]:
    """Public accessor for the dashboard."""
    with _lock:
        return _read_all()


def clear() -> int:
    """Wipes all user-submitted comments. Returns how many were removed."""
    with _lock:
        existing = _read_all()
        count = len(existing)
        _write_all([])
    logger.info(f"[USER_COMMENT] Cleared {count} entries")
    return count
