"""
utils/replied_store.py
----------------------
Production duplicate-reply guard.

Persists the IDs of comments Shelby's bot has already replied to, so the hourly
comment_reply run never replies twice — even if Apify hasn't yet surfaced the
new reply inside the comment's `replies` array (the only guard we'd otherwise
have in live mode).

The file lives next to config.json (same persistent volume in production) so
the record survives redeploys. This guard is used only in LIVE mode; DRY_RUN
demos rely on the rotating mock fixtures + user_comments flags instead, so we
never write here during a dry run (keeps the demo's comment variety intact).
"""

import json
import logging
import os
from threading import Lock

logger = logging.getLogger(__name__)


def _default_path() -> str:
    """Place the store beside config.json so it shares the persistent volume."""
    cfg = os.environ.get("CONFIG_PATH")
    base = (
        os.path.dirname(cfg)
        if cfg
        else os.path.dirname(os.path.dirname(__file__))
    )
    return os.path.join(base, "replied_comments.json")


STORE_PATH = os.environ.get("REPLIED_STORE_PATH") or _default_path()

# Keep the file bounded. At hourly cadence this is far more than enough; oldest
# entries are trimmed first (a comment that old will never resurface).
MAX_IDS = 5000

_lock = Lock()


def _read() -> list:
    """Reads the stored ID list. Returns [] if missing/unreadable."""
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        logger.warning("replied_comments.json unreadable — treating as empty.")
        return []


def _write(ids: list) -> None:
    """Writes the ID list back, trimmed to the most recent MAX_IDS."""
    parent = os.path.dirname(STORE_PATH)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(ids[-MAX_IDS:], f)


def has_replied(comment_id: str) -> bool:
    """True if we've already recorded a reply to this comment ID."""
    if not comment_id:
        return False
    with _lock:
        return comment_id in set(_read())


def mark_replied(comment_id: str) -> None:
    """Records that we replied to this comment ID (no-op if already present)."""
    if not comment_id:
        return
    with _lock:
        ids = _read()
        if comment_id in ids:
            return
        ids.append(comment_id)
        _write(ids)
    logger.info(f"[REPLIED_STORE] Recorded reply to comment {comment_id}")
