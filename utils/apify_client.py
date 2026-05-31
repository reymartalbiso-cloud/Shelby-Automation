"""
utils/apify_client.py
---------------------
Reusable wrapper for the Apify Skool All-in-One API actor.
Handles all reading from and writing to the Skool community.

Actor: cristiantala/skool-all-in-one-api
Actor store: https://apify.com/cristiantala/skool-all-in-one-api
"""

import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── API Config ──────────────────────────────────────────────
APIFY_BASE_URL = (
    "https://api.apify.com/v2/acts/cristiantala~skool-all-in-one-api"
    "/run-sync-get-dataset-items"
)
GROUP_SLUG = "class-economy"
MAX_RETRIES = 1
RETRY_DELAY_SECONDS = 5
REQUEST_TIMEOUT = 120  # Apify runs can take longer than usual APIs


def _get_token() -> str:
    """Reads the Apify API token from environment variables."""
    token = os.getenv("APIFY_API_TOKEN")
    if not token or token == "your_apify_token_here":
        raise EnvironmentError(
            "APIFY_API_TOKEN is not set. Please add it to your .env file."
        )
    return token


def _get_skool_creds() -> tuple[str, str]:
    """
    Reads Shelby's Skool email + password from env. The Apify actor requires
    these to authenticate against Skool (cookie-based; the actor caches the
    session internally per run).
    """
    email = os.getenv("SKOOL_EMAIL")
    password = os.getenv("SKOOL_PASSWORD")
    if not email or not password:
        raise EnvironmentError(
            "SKOOL_EMAIL and SKOOL_PASSWORD must be set in .env — the Apify "
            "Skool actor needs them to log in as Shelby."
        )
    return email, password


def _is_actor_error(results) -> tuple[bool, str | None]:
    """
    Detects an actor-level failure encoded inside a single-item dataset.
    The cristiantala/skool-all-in-one-api actor reports auth/validation errors
    as `[{"success": false, "error": "...", ...}]` rather than a non-2xx HTTP
    code, so the raw HTTP layer can't catch them — we have to inspect the body.
    """
    if not isinstance(results, list) or len(results) != 1:
        return False, None
    first = results[0]
    if isinstance(first, dict) and first.get("success") is False:
        return True, first.get("error") or first.get("errorCode") or "unknown actor error"
    return False, None


def _run_actor(payload: dict) -> list | None:
    """
    Core function that sends a request to the Apify actor.

    Args:
        payload: The JSON body sent to the actor (must include 'action').

    Returns:
        A list of result items from Apify, or None on failure.
    """
    token = _get_token()
    email, password = _get_skool_creds()
    url = f"{APIFY_BASE_URL}?token={token}"

    # Inject Skool auth into every call. The actor caches the session per run,
    # so we pay the Playwright login cost once per actor invocation, not per
    # logical action. Done here (not at call sites) so callers stay simple.
    payload = {**payload, "email": email, "password": password}

    for attempt in range(1, MAX_RETRIES + 2):  # 2 total attempts
        try:
            action = payload.get("action", "unknown")
            logger.info(f"Apify call '{action}' (attempt {attempt})")

            response = requests.post(
                url,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            results = response.json()

            # The actor reports auth/input errors INSIDE the dataset, not via
            # a non-2xx HTTP. Catch that here so callers never see a fake "OK".
            errored, err_msg = _is_actor_error(results)
            if errored:
                logger.error(f"Apify '{action}' actor-level failure: {err_msg}")
                return None

            logger.info(f"Apify '{action}' success — {len(results)} item(s) returned")
            return results

        except requests.exceptions.HTTPError as e:
            logger.error(f"Apify HTTP error (attempt {attempt}): {e} — {response.text}")
        except requests.exceptions.Timeout:
            logger.error(f"Apify request timed out (attempt {attempt})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Apify request error (attempt {attempt}): {e}")

        if attempt <= MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
            time.sleep(RETRY_DELAY_SECONDS)

    logger.error(f"Apify actor failed after all retry attempts for action: {payload.get('action')}")
    return None


def _write_succeeded(result, action: str) -> bool:
    """
    Validates the dataset returned by a write action (posts:create).

    The run-sync-get-dataset-items endpoint returns whatever items the actor
    pushed. A successful create pushes the created object; a failure typically
    yields an empty dataset or an item carrying an error field. We treat both
    as failure — unlike the old `result is not None` check, which counted an
    empty list `[]` as success and could log "posted" when nothing happened.

    NOTE: confirm the exact created-id field name against the live actor once
    real credentials are available; the id logging below is best-effort.
    """
    if not result or not isinstance(result, list):
        logger.error(f"Apify '{action}' returned no items — treating as a FAILED write.")
        return False

    first = result[0]
    if isinstance(first, dict) and (first.get("error") or first.get("errorMessage")):
        err = first.get("error") or first.get("errorMessage")
        logger.error(f"Apify '{action}' reported an error: {err}")
        return False

    created_id = first.get("id") if isinstance(first, dict) else None
    if created_id:
        logger.info(f"Apify '{action}' created id={created_id}")
    return True


# ── Public Functions ─────────────────────────────────────────
#
# These wrap the four actions the live actor accepts. Field/action names below
# were validated by direct calls against cristiantala/skool-all-in-one-api:
#   posts:list         → flat groupSlug; returns ALL posts (limit ignored, we
#                        slice client-side after sorting by updatedAt desc)
#   posts:getComments  → params.postId; comments have nested `replies`
#   posts:create       → params.title + params.content + params.labelId
#   posts:createComment→ params.content + params.rootId + params.parentId
#
# Real object fields (NOT the spec's assumed names):
#   author.id     (not createdBy.id)
#   content       (not body)
#   rootId, parentId, replies   — as expected


# Skool category (label) the daily/weekly post goes into. The class-economy
# group has three labels; the 24-post default below is the main discussion
# feed. Override via SKOOL_POST_LABEL_ID in .env if you'd rather route AI
# posts to a different category.
DEFAULT_LABEL_ID = "285b3422ba63486b84b3a16f0fce8a5a"


def list_posts(limit: int = 20) -> list:
    """
    Fetches the `limit` most recent posts from the class-economy group.

    The actor doesn't honor a `limit` parameter — it returns all top-level posts
    — so we sort by `updatedAt` desc and slice client-side.
    """
    payload = {
        "action": "posts:list",
        "groupSlug": GROUP_SLUG,
    }
    result = _run_actor(payload)
    if not result:
        return []
    # Newest activity first, then truncate.
    result.sort(key=lambda p: p.get("updatedAt") or p.get("createdAt") or "", reverse=True)
    return result[:limit]


def list_comments(post_id: str) -> list:
    """
    Fetches all comments for a specific post. Each comment includes a nested
    `replies` array of any direct replies (matching the spec's filter logic).
    """
    payload = {
        "action": "posts:getComments",
        "groupSlug": GROUP_SLUG,
        "params": {"postId": post_id},
    }
    result = _run_actor(payload)
    return result if result is not None else []


def create_post(title: str, content: str, label_id: str | None = None) -> bool:
    """
    Creates a new top-level post in the class-economy community.

    Skool posts require a title AND content; the AI generates the content and
    the caller derives a short title from it (see daily_post / weekly_events).
    """
    payload = {
        "action": "posts:create",
        "groupSlug": GROUP_SLUG,
        "params": {
            "title": title,
            "content": content,
            "labelId": label_id or os.getenv("SKOOL_POST_LABEL_ID") or DEFAULT_LABEL_ID,
        },
    }
    result = _run_actor(payload)
    return _write_succeeded(result, action="posts:create")


def create_reply(content: str, root_id: str, parent_id: str) -> bool:
    """
    Posts a reply (comment) to a specific comment under a post.

    `root_id` is the original post; `parent_id` is the comment being replied
    to (for a top-level comment on a post, parent_id == root_id).
    """
    payload = {
        "action": "posts:createComment",
        "groupSlug": GROUP_SLUG,
        "params": {
            "content": content,
            "rootId": root_id,
            "parentId": parent_id,
        },
    }
    result = _run_actor(payload)
    return _write_succeeded(result, action="posts:createComment")
