"""
Sovereign Agent - Seamless Update Manager v3.0
Downloads and applies updates without user intervention.
Supports both Git-based (developer) and Installer-based (production) update paths.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

# Tracking Update State
_update_available = False
_latest_version = ""
_download_url = ""

def _get_config():
    """Lazy import to avoid circular dependency."""
    import config
    return config

def _get_data_paths():
    """Get the persistent data paths from config."""
    cfg = _get_config()
    return {
        "base_data": cfg.BASE_DATA_PATH,
        "data_dir": cfg.DATA_DIR,
        "env_path": cfg.ENV_PATH,
    }

def _is_frozen():
    """Check if running as a PyInstaller bundle (installed EXE)."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')

def _get_app_dir():
    """Get the application installation directory."""
    if _is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).parent.parent

# ─── GitHub API ──────────────────────────────────────────────

def get_latest_release_info() -> dict:
    """Fetch full release info from GitHub API."""
    cfg = _get_config()
    url = f"https://api.github.com/repos/{cfg.GITHUB_REPO}/releases/latest"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SovereignAgent"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception:
        return {}

def get_latest_github_version() -> str:
    """Fetch the latest release tag from GitHub API."""
    data = get_latest_release_info()
    return data.get("tag_name", "").replace("v", "")

def _get_installer_download_url(release_info: dict) -> str:
    """Extract the .exe installer URL from release assets."""
    for asset in release_info.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".exe") and "setup" in name:
            return asset.get("browser_download_url", "")
    return ""

def _get_portable_download_url(release_info: dict) -> str:
    """Extract the portable .zip URL from release assets."""
    for asset in release_info.get("assets", []):
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and "portable" in name:
            return asset.get("browser_download_url", "")
    return ""

# ─── Version Comparison ─────────────────────────────────────

def _version_is_newer(remote: str, local: str) -> bool:
    """Semantic version comparison. Returns True if remote > local."""
    try:
        remote_parts = [int(p) for p in remote.split(".")]
        local_parts = [int(p) for p in local.split(".")]
        return remote_parts > local_parts
    except (ValueError, AttributeError):
        return remote != local and bool(remote)

# ─── Check for Updates ──────────────────────────────────────

def check_for_updates() -> bool:
    """
    Non-blocking check: Queries GitHub for a newer version.
    Returns True if an update is available.
    """
    global _update_available, _latest_version, _download_url
    cfg = _get_config()

    release_info = get_latest_release_info()
    latest_v = release_info.get("tag_name", "").replace("v", "")

    if latest_v and _version_is_newer(latest_v, cfg.VERSION):
        _update_available = True
        _latest_version = latest_v
        # Prefer installer for frozen apps, portable zip as fallback
        if _is_frozen():
            _download_url = _get_installer_download_url(release_info) or _get_portable_download_url(release_info)
        else:
            _download_url = ""  # Git-based update, no download needed
        return True

    # Fallback: Check git status for developers
    if not _is_frozen():
        try:
            app_dir = _get_app_dir()
            if (app_dir / ".git").exists():
                subprocess.run(["git", "fetch"], cwd=app_dir, capture_output=True, timeout=10)
                result = subprocess.run(
                    ["git", "status", "-uno"],
                    cwd=app_dir, capture_output=True, text=True, timeout=5
                )
                if "your branch is behind" in result.stdout.lower():
                    _update_available = True
                    return True
        except Exception:
            pass

    return _update_available

def is_update_pending() -> bool:
    """Getter for internal update state."""
    return _update_available

def get_update_info() -> dict:
    """Get details about the available update."""
    return {
        "available": _update_available,
        "version": _latest_version,
        "download_url": _download_url,
        "is_frozen": _is_frozen(),
    }

# ─── Seamless Update Execution ──────────────────────────────

def backup_state():
    """Create a safety snapshot of user data before update."""
    paths = _get_data_paths()
    backup_dir = paths["base_data"] / "update_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    save_path = backup_dir / f"pre_update_{timestamp}"
    save_path.mkdir(exist_ok=True)

    # Critical files to safeguard
    critical_files = [
        paths["env_path"],
        paths["data_dir"] / "applications.db",
        paths["data_dir"] / "profile.yaml",
        paths["data_dir"] / "identity.yaml",
    ]

    preserved = 0
    for src in critical_files:
        if src.exists():
            try:
                shutil.copy2(src, save_path / src.name)
                preserved += 1
            except Exception:
                pass

    if preserved > 0:
        print(f"  ✓ State backup created: {preserved} files preserved.")

    # Prune old backups (keep last 3)
    try:
        backups = sorted(backup_dir.glob("pre_update_*"), key=os.path.getmtime)
        for old in backups[:-3]:
            shutil.rmtree(old, ignore_errors=True)
    except Exception:
        pass

    return save_path


def _download_file(url: str, dest: Path, progress_callback=None) -> bool:
    """Download a file from URL with optional progress callback."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SovereignAgent"})
        with urllib.request.urlopen(req, timeout=120) as response:
            total = int(response.headers.get("Content-Length", 0))
            downloaded = 0
            block_size = 8192

            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        progress_callback(downloaded / total)

        return dest.exists() and dest.stat().st_size > 0
    except Exception as e:
        print(f"  ✗ Download failed: {e}")
        return False


def apply_update_seamless(progress_callback=None) -> dict:
    """
    Seamless update engine:
    - For EXE installs: Downloads new installer and runs it silently
    - For Git dev: Performs git pull + restart
    
    Returns dict with keys: success, message, requires_restart
    """
    cfg = _get_config()
    
    if not _update_available:
        return {"success": False, "message": "No update available.", "requires_restart": False}

    # Step 1: Backup
    print("[Update] Phase 1: Safeguarding mission state...")
    backup_state()

    # Step 2: Apply update based on environment
    if _is_frozen() and _download_url:
        return _apply_installer_update(progress_callback)
    else:
        return _apply_git_update()


def _apply_installer_update(progress_callback=None) -> dict:
    """Download the latest installer and launch it for seamless upgrade."""
    print(f"[Update] Phase 2: Downloading Sovereign Agent v{_latest_version}...")

    # Download to a temp location
    temp_dir = Path(tempfile.mkdtemp(prefix="sovereign_update_"))
    installer_name = f"Sovereign_Agent_Setup_v{_latest_version.replace('.', '_')}.exe"
    installer_path = temp_dir / installer_name

    success = _download_file(_download_url, installer_path, progress_callback)

    if not success:
        return {
            "success": False,
            "message": "Download failed. Check your internet connection.",
            "requires_restart": False,
        }

    print(f"[Update] Phase 3: Launching silent installer...")

    try:
        # Launch the Inno Setup installer in silent mode
        # /SILENT = shows progress bar, no interaction
        # /CLOSEAPPLICATIONS = closes running instance
        # /RESTARTAPPLICATIONS = restarts after install
        # /NORESTART = don't restart Windows
        subprocess.Popen(
            [
                str(installer_path),
                "/SILENT",
                "/CLOSEAPPLICATIONS",
                "/RESTARTAPPLICATIONS",
                "/NORESTART",
            ],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
            if os.name == "nt" else 0,
        )

        return {
            "success": True,
            "message": f"Update v{_latest_version} downloading and installing. The app will restart automatically.",
            "requires_restart": True,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to launch installer: {e}",
            "requires_restart": False,
        }


def _apply_git_update() -> dict:
    """Pull latest code from GitHub and signal restart."""
    app_dir = _get_app_dir()

    if not (app_dir / ".git").exists():
        return {
            "success": False,
            "message": "Not a git repository. Please download the latest release manually.",
            "requires_restart": False,
        }

    print("[Update] Phase 2: Synchronizing mission code from GitHub...")

    try:
        # Stash any local changes to prevent merge conflicts
        subprocess.run(["git", "stash"], cwd=app_dir, capture_output=True, timeout=10)

        result = subprocess.run(
            ["git", "pull", "--rebase"],
            cwd=app_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            print(f"  ✓ Code synchronized: {result.stdout.strip()}")

            # Attempt to install any new dependencies
            req_file = app_dir / "requirements.txt"
            if req_file.exists():
                print("[Update] Phase 3: Checking for new dependencies...")
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", str(req_file), "-q"],
                    cwd=app_dir,
                    capture_output=True,
                    timeout=60,
                )

            return {
                "success": True,
                "message": f"Updated to v{_latest_version}. Please restart the application.",
                "requires_restart": True,
            }
        else:
            # Try to pop stash if pull failed
            subprocess.run(["git", "stash", "pop"], cwd=app_dir, capture_output=True, timeout=5)
            return {
                "success": False,
                "message": f"Git pull failed: {result.stderr.strip()}",
                "requires_restart": False,
            }

    except Exception as e:
        return {
            "success": False,
            "message": f"Update error: {e}",
            "requires_restart": False,
        }


def restart_application():
    """Restart the application after a successful update."""
    print("[Update] Restarting Sovereign Agent...")
    time.sleep(1)

    if _is_frozen():
        # Re-launch the executable
        exe_path = sys.executable
        try:
            subprocess.Popen(
                [exe_path],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt" else 0,
            )
        except Exception as e:
            print(f"[Update] Auto-restart failed: {e}. Please restart manually.")
            return
    else:
        # Re-launch the Python script
        try:
            subprocess.Popen(
                [sys.executable] + sys.argv,
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
                if os.name == "nt" else 0,
            )
        except Exception as e:
            print(f"[Update] Auto-restart failed: {e}. Please restart manually.")
            return

    sys.exit(0)


# ─── CLI Entry Point ────────────────────────────────────────

def main():
    """CLI update command."""
    print("═══ Sovereign Update Manager v3.0 ═══")

    cfg = _get_config()
    print(f"  Current Version: v{cfg.VERSION}")
    print(f"  Environment: {'Installed (EXE)' if _is_frozen() else 'Developer (Git)'}")

    print("\n  🔍 Checking for updates...")
    if check_for_updates():
        info = get_update_info()
        print(f"\n  ⚡ UPDATE AVAILABLE: v{info['version']}")

        result = apply_update_seamless()
        if result["success"]:
            print(f"\n  ✓ {result['message']}")
            if result["requires_restart"] and not _is_frozen():
                restart_application()
        else:
            print(f"\n  ✗ {result['message']}")
    else:
        print("  ✓ You are running the latest version.")


if __name__ == "__main__":
    main()
