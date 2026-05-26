"""
utils/toggle.py
---------------
Reads config.json and returns whether the system is currently active.
All three workflow scripts call is_system_active() as their very first step.
If it returns False, the script exits immediately without making any API calls.
"""

import json
import os
import logging

# Path to config.json — always relative to the project root
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

logger = logging.getLogger(__name__)


def _read_config() -> dict:
    """Reads config.json and returns it as a dict. Returns empty dict on failure."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"config.json not found at {CONFIG_PATH}.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"config.json is malformed: {e}.")
        return {}


def is_system_active() -> bool:
    """
    Reads SYSTEM_ACTIVE from config.json.

    Returns:
        True  — system is on, proceed with workflow
        False — system is paused, exit immediately
    """
    config = _read_config()
    active = config.get("SYSTEM_ACTIVE", False)
    if not active:
        logger.info("System is PAUSED (SYSTEM_ACTIVE = false). Exiting.")
    return bool(active)


def is_mock_claude() -> bool:
    """
    Reads MOCK_CLAUDE from config.json.
    When true, claude_client.generate_content returns canned Shelby-voice
    fixtures instead of calling the real Anthropic API. Useful for $0 testing.
    """
    return bool(_read_config().get("MOCK_CLAUDE", False))


def is_dry_run() -> bool:
    """
    Reads DRY_RUN from config.json.
    When true, apify_client write functions log what they would have posted
    and return success without calling Apify. Read functions return mock data.
    """
    return bool(_read_config().get("DRY_RUN", False))


def set_system_active(value: bool) -> bool:
    """
    Updates SYSTEM_ACTIVE in config.json.
    Used by the toggle dashboard to flip the switch.

    Args:
        value: True to activate, False to pause

    Returns:
        True if the update succeeded, False otherwise
    """
    try:
        # Read existing config first to preserve other settings
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config = {}

        config["SYSTEM_ACTIVE"] = value

        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)

        state = "ACTIVE" if value else "PAUSED"
        logger.info(f"System state changed to: {state}")
        return True

    except Exception as e:
        logger.error(f"Failed to update config.json: {e}")
        return False
