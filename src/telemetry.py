import os
import uuid
import requests
import threading
import json
import sys
from pathlib import Path
from datetime import datetime

# Local config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

def _get_or_create_user_id():
    """Generate a persistent, anonymous UUID for this installation."""
    uid_path = config.DATA_DIR / "device_id.txt"
    if uid_path.exists():
        return uid_path.read_text().strip()
    
    new_id = str(uuid.uuid4())
    uid_path.write_text(new_id)
    return new_id

USER_ID = _get_or_create_user_id()

def log_event(event_name, properties=None):
    """
    Log an anonymous event to Supabase telemetry.
    Only logs if TELEMETRY_ENABLED is True and keys are provided.
    """
    if not config.TELEMETRY_ENABLED:
        return
        
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        # Silently skip if developer hasn't set up the keys yet
        return

    # Prepare safe, anonymous payload for the Supabase 'telemetry' table
    payload = {
        "user_id": USER_ID,
        "event_name": event_name,
        "os": sys.platform,
        "llm_provider": config.LLM_PROVIDER,
        "version": config.VERSION,
        "properties": json.dumps(properties) if properties else "{}"
    }

    # REST endpoint for the 'telemetry' table
    url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/telemetry"
    headers = {
        "apikey": config.SUPABASE_KEY,
        "Authorization": f"Bearer {config.SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal"
    }

    def _send():
        try:
            requests.post(url, json=payload, headers=headers, timeout=5)
        except Exception:
            pass

    # Fire and forget in a daemon thread
    threading.Thread(target=_send, daemon=True).start()

def log_success():
    log_event("application_applied")

def log_search(results_count):
    log_event("job_search_completed", {"results_count": results_count})

def log_error(error_code):
    log_event("system_error", {"error_code": str(error_code)})
