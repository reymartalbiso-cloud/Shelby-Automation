"""
utils/claude_client.py
----------------------
Reusable wrapper for the Anthropic Claude API.
All content generation in this project goes through this module.

Model: claude-sonnet-4-6
API docs: https://docs.anthropic.com/en/api/messages

Note: the original client spec named `claude-sonnet-4-20250514`, which Anthropic
does not publish (the endpoint returns 404 for it). We use the current Sonnet
4.6 alias instead — the closest in-family substitute.
"""

import os
import re
import time
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ── API Config ──────────────────────────────────────────────
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-6"
ANTHROPIC_VERSION = "2023-06-01"
MAX_RETRIES = 1
RETRY_DELAY_SECONDS = 5


def _sanitize_output(text: str) -> str:
    """
    Strip AI-tell formatting from generated content before it goes out.

    Two classes of "tells" are removed here:

    1. Em-dashes (—) and en-dashes (–) — one of the most recognizable signs of
       AI writing. Replaced with natural punctuation.

    2. Markdown emphasis (**bold**, *italic*, __bold__, `code`) — Skool renders
       posts as plain text, so these characters show up literally as asterisks
       and underscores in the feed. We strip the wrappers but keep the inner
       words intact.

    Even with explicit prompt rules forbidding both, the model occasionally
    slips. This belt-and-suspenders pass runs on EVERY Claude response so
    anyone reading the post or reply sees only clean Shelby-voice text.
    """
    if not text:
        return text

    # ---- Dashes ----
    # Spaced dashes (most common em-dash usage) become a comma + space.
    text = text.replace(" — ", ", ").replace(" – ", ", ")
    # Unspaced em-dash (e.g. "word—word") becomes ", ".
    text = text.replace("—", ", ")
    # Unspaced en-dash (often number ranges like "7–10") becomes a hyphen.
    text = text.replace("–", "-")

    # ---- Markdown emphasis ----
    # Bold first so it's consumed before the italic pass sees a stray `*`.
    # The inner pattern forbids the wrapper char + newlines so we never span
    # paragraphs or merge unrelated formatting blocks.
    text = re.sub(r"\*\*([^*\n]+?)\*\*", r"\1", text)   # **bold**
    text = re.sub(r"__([^_\n]+?)__", r"\1", text)       # __bold__
    # Single-asterisk italic. Lookaround keeps us from eating any leftover **.
    text = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"\1", text)
    # Inline `code` — backticks have no rendering on Skool either.
    text = re.sub(r"`([^`\n]+?)`", r"\1", text)

    # ---- Tidy up ----
    while ", ," in text:
        text = text.replace(", ,", ",")
    while "  " in text:
        text = text.replace("  ", " ")
    return text


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
            text = _sanitize_output(text)
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
