"""
dashboard/app.py
----------------
AI Shelby Toggle Dashboard — Lightweight Flask web server.

This provides a simple web UI that lets Shelby (or the project owner)
pause and resume the entire automation system without touching any code.

Routes:
  GET  /           — Serves the toggle dashboard UI
  GET  /api/status — Returns the current SYSTEM_ACTIVE state as JSON
  POST /api/toggle — Flips SYSTEM_ACTIVE in config.json

To run locally:
  cd ai-shelby
  python dashboard/app.py

To run in production (Render/Railway):
  Use the command: python dashboard/app.py
  And set the PORT environment variable (defaults to 5000).
"""

import os
import subprocess
import sys
import logging
import threading

from flask import Flask, jsonify, render_template, request

# ── Add parent directory to path so we can import utils ──────
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from utils.toggle import is_system_active, set_system_active
from utils.mock_feed import read_all as read_feed, clear as clear_feed, append_community_comment
from utils.user_comments import add as add_user_comment
from utils.mock_fixtures import MOCK_POSTS

# ── Flask App Setup ───────────────────────────────────────────
app = Flask(__name__, template_folder="templates")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("dashboard")


# ── Routes ────────────────────────────────────────────────────

@app.route("/")
def index():
    """Serves the main toggle dashboard page."""
    active = is_system_active()
    return render_template("index.html", system_active=active)


@app.route("/api/status", methods=["GET"])
def get_status():
    """
    Returns the current system state.

    Response:
        { "SYSTEM_ACTIVE": true | false }
    """
    active = is_system_active()
    logger.info(f"Status check — SYSTEM_ACTIVE: {active}")
    return jsonify({"SYSTEM_ACTIVE": active})


def _seconds_between(ts_a: str, ts_b: str) -> int | None:
    """Returns the absolute number of seconds between two ISO timestamps, or None on parse error."""
    from datetime import datetime
    try:
        return abs(int((datetime.fromisoformat(ts_b) - datetime.fromisoformat(ts_a)).total_seconds()))
    except (ValueError, TypeError):
        return None


def _build_threads(entries: list[dict]) -> list[dict]:
    """
    Groups community_comment + matching reply entries into single threads
    so the feed page can render them as one combined card.

    Returns a list of thread dicts, each shaped:
      { "kind": "thread", "comment": {...}, "reply": {...} | None, "latency_s": int | None, "timestamp": iso }
      { "kind": "post",    "entry": {...}, "timestamp": iso }
      { "kind": "orphan_reply", "entry": {...}, "timestamp": iso }   # rare
    """
    # Index replies by the comment they target
    replies_by_parent = {}
    for e in entries:
        if e.get("type") == "reply":
            pid = e.get("parent_id")
            if pid:
                replies_by_parent[pid] = e

    # Track which reply entries got attached so we don't render them twice
    attached_reply_ids = set()
    threads = []

    for e in entries:
        etype = e.get("type")
        ts = e.get("timestamp", "")

        if etype == "community_comment":
            reply = replies_by_parent.get(e.get("comment_id"))
            if reply:
                attached_reply_ids.add(id(reply))
            latency = (
                _seconds_between(ts, reply["timestamp"])
                if reply else None
            )
            # Sort the thread by its latest activity (reply timestamp if present)
            sort_ts = reply["timestamp"] if reply else ts
            threads.append({
                "kind": "thread",
                "comment": e,
                "reply": reply,
                "latency_s": latency,
                "timestamp": sort_ts,
            })

        elif etype == "reply":
            # Will be attached to its comment in a later pass — skip for now
            continue

        else:  # post
            threads.append({
                "kind": "post",
                "entry": e,
                "timestamp": ts,
            })

    # Any reply that wasn't attached to a community_comment is an orphan
    # (happens if the comment entry was cleared but the reply remained, or
    # if the system replied before the comment was logged). Render it solo.
    for e in entries:
        if e.get("type") == "reply" and id(e) not in attached_reply_ids:
            threads.append({
                "kind": "orphan_reply",
                "entry": e,
                "timestamp": e.get("timestamp", ""),
            })

    # Newest activity at the top
    threads.sort(key=lambda t: t["timestamp"], reverse=True)
    return threads


@app.route("/feed")
def feed():
    """Serves the mock Skool feed — posts/replies captured during DRY_RUN."""
    entries = read_feed()
    threads = _build_threads(entries)
    return render_template("feed.html", threads=threads, entries=entries, count=len(entries))


@app.route("/api/feed", methods=["GET"])
def api_feed():
    """Returns the raw feed JSON (used by the page's auto-refresh)."""
    return jsonify({"entries": read_feed()})


@app.route("/api/clear-feed", methods=["POST"])
def api_clear_feed():
    """Wipes the mock feed."""
    removed = clear_feed()
    return jsonify({"success": True, "removed": removed})


@app.route("/api/posts", methods=["GET"])
def api_posts():
    """Returns the list of mock Shelby posts the user can comment on."""
    return jsonify({
        "posts": [
            {
                "id": p["id"],
                "preview": (p.get("body", "") or "")[:80],
            }
            for p in MOCK_POSTS
        ]
    })


def _trigger_comment_reply_async() -> None:
    """
    Kicks off comment_reply.py as a subprocess in a background thread so the
    user sees Shelby's reply within seconds of submitting a comment, instead
    of having to wait up to 5 minutes for the next scheduler cycle.
    """
    def run():
        script = os.path.join(PROJECT_ROOT, "comment_reply.py")
        try:
            subprocess.run(
                [sys.executable, script],
                cwd=PROJECT_ROOT,
                timeout=120,
            )
            logger.info("Triggered comment_reply.py completed")
        except subprocess.TimeoutExpired:
            logger.error("Triggered comment_reply.py timed out after 120s")
        except Exception as e:
            logger.error(f"Triggered comment_reply.py failed: {e}")

    threading.Thread(target=run, daemon=True).start()
    logger.info("Triggered comment_reply.py in background")


@app.route("/api/add-comment", methods=["POST"])
def api_add_comment():
    """
    Accepts a user-submitted comment, stores it for the comment_reply
    workflow to pick up, mirrors it onto the visible feed immediately, and
    kicks off a one-shot comment_reply.py run so the user sees Shelby's
    reply within seconds.

    Request JSON: { "body": "...", "post_id": "post_001", "author_name": "..." }
    """
    body_json = request.get_json(silent=True) or {}
    body = (body_json.get("body") or "").strip()
    post_id = (body_json.get("post_id") or "").strip()
    author_name = (body_json.get("author_name") or "Test Teacher").strip()

    if not body:
        return jsonify({"success": False, "error": "Comment body is required"}), 400

    valid_post_ids = {p["id"] for p in MOCK_POSTS}
    if post_id not in valid_post_ids:
        post_id = MOCK_POSTS[0]["id"]  # default to the first mock post

    # Persist so comment_reply.py picks it up
    entry = add_user_comment(body=body, post_id=post_id, author_name=author_name)

    # Mirror onto the visible feed instantly (so the user sees their own comment
    # before the reply arrives)
    append_community_comment(
        body=entry["body"],
        comment_id=entry["id"],
        root_id=post_id,
        author_name=entry["author_name"],
        author_id=entry["author_id"],
    )

    # Kick off Shelby's reply asynchronously
    _trigger_comment_reply_async()

    return jsonify({
        "success": True,
        "comment_id": entry["id"],
        "post_id": post_id,
        "author_name": entry["author_name"],
    })


@app.route("/api/toggle", methods=["POST"])
def toggle():
    """
    Flips the SYSTEM_ACTIVE state in config.json.

    Optional JSON body: { "value": true | false }
    If no body provided, it toggles the current state.

    Response:
        { "SYSTEM_ACTIVE": true | false, "success": true | false }
    """
    try:
        body = request.get_json(silent=True) or {}
        if "value" in body:
            # Explicit value provided
            new_value = bool(body["value"])
        else:
            # Toggle current value
            new_value = not is_system_active()

        success = set_system_active(new_value)
        state = "ACTIVE" if new_value else "PAUSED"
        logger.info(f"System toggled to: {state}")

        return jsonify({"SYSTEM_ACTIVE": new_value, "success": success})

    except Exception as e:
        logger.error(f"Toggle error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ── Run Server ────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Starting AI Shelby Dashboard on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
