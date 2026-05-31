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
import sys
import logging

from flask import Flask, jsonify, render_template, request

# ── Add parent directory to path so we can import utils ──────
PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, PROJECT_ROOT)

from utils.toggle import is_system_active, set_system_active, ensure_config

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
    # Make sure a toggle file exists before anything reads it (fresh volume).
    ensure_config()

    port = int(os.environ.get("PORT", 5000))

    # In the combined-service model, the scheduler runs in this same process so
    # the dashboard and the workflows share one filesystem (and one config.json).
    # Set RUN_SCHEDULER=false to run the dashboard alone — e.g. during local
    # DRY_RUN demos where test_scheduler.py drives the workflows instead.
    if os.environ.get("RUN_SCHEDULER", "true").lower() in ("1", "true", "yes"):
        from scheduler import start_background_scheduler
        start_background_scheduler()
        logger.info("In-process scheduler is running alongside the dashboard.")
    else:
        logger.info("RUN_SCHEDULER is off — serving dashboard only, no scheduling.")

    logger.info(f"Starting AI Shelby Dashboard on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
