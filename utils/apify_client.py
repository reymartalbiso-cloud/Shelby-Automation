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


def _run_actor(payload: dict) -> list | None:
    """
    Core function that sends a request to the Apify actor.

    Args:
        payload: The JSON body sent to the actor (must include 'action').

    Returns:
        A list of result items from Apify, or None on failure.
    """
    token = _get_token()
    url = f"{APIFY_BASE_URL}?token={token}"

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


# ── Public Functions ─────────────────────────────────────────


def list_posts(limit: int = 20) -> list:
    """
    Fetches the most recent posts from the class-economy group.

    Args:
        limit: How many posts to fetch (default 20).

    Returns:
        List of post objects, or empty list on failure.
    """
    from utils.toggle import is_dry_run
    if is_dry_run():
        from utils.mock_fixtures import MOCK_POSTS
        logger.info(f"[DRY_RUN] Returning {len(MOCK_POSTS)} mock posts (no Apify call)")
        return MOCK_POSTS[:limit]

    payload = {
        "action": "posts:list",
        "groupSlug": GROUP_SLUG,
        "limit": limit,
    }
    result = _run_actor(payload)
    return result if result is not None else []


def list_comments(post_id: str) -> list:
    """
    Fetches all comments/replies for a specific post.

    Args:
        post_id: The Skool post ID to fetch comments for.

    Returns:
        List of comment objects, or empty list on failure.
    """
    from utils.toggle import is_dry_run
    if is_dry_run():
        from utils.mock_fixtures import mock_list_comments
        comments = mock_list_comments(post_id)
        logger.info(f"[DRY_RUN] Returning {len(comments)} mock comments for post {post_id}")
        return comments

    payload = {
        "action": "posts:list",
        "groupSlug": GROUP_SLUG,
        "rootId": post_id,
    }
    result = _run_actor(payload)
    return result if result is not None else []


def create_post(body: str, category: str = "general") -> bool:
    """
    Creates a new top-level post in the class-economy Skool community.

    Args:
        body:     The post text content.
        category: Skool category slug (default "general").

    Returns:
        True if the post was created successfully, False otherwise.
    """
    from utils.toggle import is_dry_run
    if is_dry_run():
        from utils.mock_feed import append_post
        preview = body[:100].replace("\n", " ")
        logger.info(
            f"[DRY_RUN] Would have posted to Skool (category={category}, "
            f"{len(body)} chars): {preview!r}..."
        )
        append_post(body=body, category=category)
        return True

    payload = {
        "action": "posts:create",
        "groupSlug": GROUP_SLUG,
        "body": body,
        "category": category,
    }
    result = _run_actor(payload)
    return result is not None


def create_reply(body: str, root_id: str, parent_id: str) -> bool:
    """
    Posts a reply to a specific comment on a Skool post.

    Args:
        body:      The reply text content.
        root_id:   The ID of the original top-level post.
        parent_id: The ID of the specific comment being replied to.

    Returns:
        True if the reply was posted successfully, False otherwise.
    """
    from utils.toggle import is_dry_run
    if is_dry_run():
        from utils.mock_feed import append_reply
        from utils.user_comments import mark_replied
        preview = body[:100].replace("\n", " ")
        logger.info(
            f"[DRY_RUN] Would have replied to comment {parent_id} "
            f"(rootId={root_id}, {len(body)} chars): {preview!r}..."
        )
        append_reply(body=body, root_id=root_id, parent_id=parent_id)
        # If this reply targeted a user-submitted comment, flip its
        # `replied` flag so the next cycle doesn't pick it up again.
        mark_replied(parent_id)
        return True

    payload = {
        "action": "posts:create",
        "groupSlug": GROUP_SLUG,
        "body": body,
        "rootId": root_id,
        "parentId": parent_id,
    }
    result = _run_actor(payload)
    return result is not None
