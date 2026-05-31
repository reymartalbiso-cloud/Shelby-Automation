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

# Path to config.json. Defaults to the project root, but can be pointed at a
# mounted volume via the CONFIG_PATH env var. In the combined-service deploy,
# the dashboard and the scheduled jobs run in ONE process on ONE filesystem,
# so this single file is the shared source of truth for the on/off toggle.
# On a host with a persistent volume, set CONFIG_PATH=/data/config.json so the
# toggle survives redeploys.
CONFIG_PATH = os.environ.get("CONFIG_PATH") or os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config.json"
)

# Default config — matches the client spec exactly: a single SYSTEM_ACTIVE flag.
DEFAULT_CONFIG = {
    "SYSTEM_ACTIVE": True,
}

logger = logging.getLogger(__name__)


def ensure_config() -> None:
    """
    Creates config.json with safe production defaults if it doesn't exist yet.

    Called once at service startup so a fresh deploy/volume always has a toggle
    file to read. Existing files are never touched — Shelby's saved on/off state
    is preserved across restarts.
    """
    if os.path.exists(CONFIG_PATH):
        return
    try:
        parent = os.path.dirname(CONFIG_PATH)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        logger.info(f"Seeded new config.json at {CONFIG_PATH} with production defaults.")
    except Exception as e:
        logger.error(f"Could not create config.json at {CONFIG_PATH}: {e}")


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
