"""
utils/claude_client.py
----------------------
Reusable wrapper for the Anthropic Claude API.
All content generation in this project goes through this module.

Model: claude-sonnet-4-20250514
API docs: https://docs.anthropic.com/en/api/messages
"""

import os
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── API Config ──────────────────────────────────────────────
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"
ANTHROPIC_VERSION = "2023-06-01"
MAX_RETRIES = 1
RETRY_DELAY_SECONDS = 5


def _get_api_key() -> str:
    """Reads the Anthropic API key from environment variables."""
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key or key == "your_anthropic_api_key_here":
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Please add it to your .env file."
        )
    return key


def generate_content(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 500,
) -> str | None:
    """
    Calls the Anthropic Claude API and returns the generated text.

    Args:
        system_prompt: The Shelby system prompt that defines tone/personality.
        user_message:  The specific instruction for what to generate.
        max_tokens:    Maximum tokens in the response (500 for posts, 200 for
                       replies, 600 for events).

    Returns:
        The generated text string, or None if both attempts fail.
    """
    # Short-circuit: if MOCK_CLAUDE is on in config.json, return a hand-tuned
    # Shelby-voice fixture instead of hitting the real Anthropic API. This is
    # how we test for $0 before the client provides a funded API key.
    from utils.toggle import is_mock_claude
    from utils.mock_fixtures import select_mock_response

    if is_mock_claude():
        mock_text = select_mock_response(user_message)
        logger.info(
            f"[MOCK_CLAUDE] Returning fixture ({len(mock_text)} chars) — "
            f"no Anthropic API call made."
        )
        return mock_text

    api_key = _get_api_key()

    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_message}
        ],
    }

    for attempt in range(1, MAX_RETRIES + 2):  # 2 total attempts
        try:
            logger.info(f"Claude API call (attempt {attempt}) — max_tokens={max_tokens}")
            response = requests.post(
                CLAUDE_API_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            data = response.json()
            text = data["content"][0]["text"]
            logger.info(f"Claude API success — generated {len(text)} characters")
            return text

        except requests.exceptions.HTTPError as e:
            logger.error(f"Claude API HTTP error (attempt {attempt}): {e} — {response.text}")
        except requests.exceptions.Timeout:
            logger.error(f"Claude API timed out (attempt {attempt})")
        except requests.exceptions.RequestException as e:
            logger.error(f"Claude API request error (attempt {attempt}): {e}")
        except (KeyError, IndexError) as e:
            logger.error(f"Unexpected Claude API response format (attempt {attempt}): {e}")

        if attempt <= MAX_RETRIES:
            logger.info(f"Retrying in {RETRY_DELAY_SECONDS} seconds...")
            time.sleep(RETRY_DELAY_SECONDS)

    logger.error("Claude API failed after all retry attempts. Skipping this action.")
    return None
