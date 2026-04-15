import requests
import json
import os
import sys
from datetime import datetime

# Local config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from src.telemetry import USER_ID

def send_discord_feedback(message, category="Bug Report"):
    """
    Sends a formatted feedback embed to the Discord webhook.
    """
    # Placeholder for the developer's webhook
    webhook_url = os.getenv("DISCORD_FEEDBACK_URL", "")
    
    if not webhook_url:
        print("[System] Discord Webhook URL not set. Feedback could not be sent.")
        return False
        
    embed = {
        "title": f"📥 New Feedback: {category}",
        "description": message,
        "color": 3447003,  # Blue
        "fields": [
            {"name": "User ID", "value": f"`{USER_ID}`", "inline": True},
            {"name": "OS", "value": sys.platform, "inline": True},
            {"name": "LLM Provider", "value": config.LLM_PROVIDER, "inline": True},
            {"name": "App Version", "value": config.VERSION, "inline": True}
        ],
        "footer": {
            "text": f"JobBot Feedback System • {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
    }
    
    payload = {
        "username": "JobBot Feedback Bot",
        "embeds": [embed]
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        if response.status_code in [200, 204]:
            print("[System] Feedback sent successfully! Thank you.")
            return True
        else:
            print(f"[System] Discord error ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"[System] Failed to send feedback: {e}")
        return False

def check_for_github_updates():
    """
    Checks the GitHub repository for the latest release version.
    """
    repo = config.GITHUB_REPO
    if not repo:
        return None
        
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("tag_name", "").replace("v", "")
            return latest_version
    except Exception:
        pass
    return None
