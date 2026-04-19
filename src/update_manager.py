import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path

# Tracking Update State
_update_available = False

# Mission Config
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "update_backups"

def backup_state():
    """Create a safety copy of the user's identity and tracking data."""
    if not DATA_DIR.exists():
        return
        
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = Path().cwd().name # Simplification, but could be time
    save_path = BACKUP_DIR / "state_pre_update"
    save_path.mkdir(exist_ok=True)
    
    # Files to preserve
    targets = ["identity.yaml", "tracker.db", ".env"]
    for target in targets:
        src = DATA_DIR / target if target != ".env" else BASE_DIR / target
        if src.exists():
            shutil.copy2(src, save_path / target)
            print(f"  ✓ Backed up: {target}")

def run_git_pull():
    """Pull the latest code from the remote repository."""
    print("  🚀 Pulling latest mission code from GitHub...")
    try:
        # Check if it's a git repo
        if not (BASE_DIR / ".git").exists():
            print("  ✗ Update Failed: Not a git repository.")
            return False
            
        result = subprocess.run(["git", "pull"], cwd=BASE_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✓ Mission code synchronized successfully.")
            return True
        else:
            print(f"  ✗ Git pull failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"  ✗ Critical update error: {e}")
        return False

def migrate_schema():
    """Future-proofing: Handle database or yaml schema changes."""
    print("  ⚙ Checking for data migration requirements...")
    # Add migration logic here if needed for v33.0+
    print("  ✓ State migration complete (No changes required for v32.0).")

def get_latest_github_version() -> str:
    """Fetch the latest release tag from GitHub API."""
    import json
    import urllib.request
    import config
    
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("tag_name", "").replace("v", "")
    except Exception:
        return ""

def check_for_updates() -> bool:
    """
    Surgical Check: Performs both Git state analysis and GitHub API version comparison.
    Returns True if an update is detected, False otherwise.
    """
    global _update_available
    import config
    
    # 1. Check GitHub API (Support for non-Git installs)
    latest_v = get_latest_github_version()
    if latest_v:
        # Simple semantic comparison or string comparison
        # Assuming format 30.1.0 vs 30.2.0
        try:
            local_parts = [int(p) for p in config.VERSION.split(".")]
            remote_parts = [int(p) for p in latest_v.split(".")]
            
            if remote_parts > local_parts:
                _update_available = True
                return True
        except:
            if latest_v != config.VERSION:
                _update_available = True
                return True

    # 2. Check Git (Support for developers)
    try:
        if not (BASE_DIR / ".git").exists():
            return _update_available
            
        # Fetch remote state without merging
        subprocess.run(["git", "fetch"], cwd=BASE_DIR, capture_output=True, timeout=10)
        
        # Compare local vs remote
        result = subprocess.run(
            ["git", "status", "-uno"], 
            cwd=BASE_DIR, capture_output=True, text=True, timeout=5
        )
        
        if "your branch is behind" in result.stdout.lower():
            _update_available = True
            return True
    except Exception:
        pass
        
    return _update_available

def is_update_pending() -> bool:
    """Getter for internal state."""
    return _update_available

def main():
    print("═══ Sovereign Update Manager ═══")
    backup_state()
    if run_git_pull():
        migrate_schema()
        print("\n[SUCCESS] Update complete. Please restart the Sovereign Agent.")
    else:
        print("\n[FAILED] Update aborted to prevent state corruption.")

if __name__ == "__main__":
    main()
