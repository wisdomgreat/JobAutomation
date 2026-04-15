import shutil
import time
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import config

def reset_application_tracker():
    """
    Safely wipes the application history (the tracker database) and recreates schema.
    Returns True if success.
    """
    db_path = config.PROJECT_ROOT / "data" / "applications.db"
    if db_path.exists():
        try:
            # Explicitly delete the file (Tracker class handles recreation)
            os.remove(db_path)
            # Phase 24.1: Re-initialize the DB immediately so ghost processes don't hit empty files
            from src.tracker import Tracker
            Tracker(db_path)
            return True
        except Exception as e:
            print(f"  [!] Failed to reset tracker: {e}")
            return False
    return True


def purge_old_outputs(days_to_keep: int = 14) -> tuple[int, int]:
    """
    Deletes folders in output/ that are older than days_to_keep.
    Returns (folders_deleted, space_cleared_mb).
    """
    if not config.OUTPUT_DIR.exists():
        return 0, 0

    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    deleted_count = 0
    total_space = 0

    # 1. Check all folders in output/
    for date_folder in config.OUTPUT_DIR.iterdir():
        if not date_folder.is_dir():
            continue
        
        # Skip archive or system folders
        if date_folder.name.startswith("_") or date_folder.name == "archive":
            continue

        try:
            # Try parsing the folder name as a date (YYYY-MM-DD)
            try:
                folder_date = datetime.strptime(date_folder.name, "%Y-%m-%d")
                should_delete = folder_date < cutoff_date
            except ValueError:
                # Fallback to filesystem metadata for complex names
                mtime = datetime.fromtimestamp(date_folder.stat().st_mtime)
                should_delete = mtime < cutoff_date
        except Exception:
            should_delete = False

        if should_delete:
            # Phase 24: Robust deletion to handle WinError 32 (file in use)
            try:
                # Calculate space before deletion
                folder_size = 0
                for f in date_folder.rglob("*"):
                    if f.is_file(): folder_size += f.stat().st_size
                
                # Use standard rmtree with error handler to handle locks or read-only
                import stat
                def on_rm_error(func, path, exc_info):
                    os.chmod(path, stat.S_IWRITE)
                    func(path)

                shutil.rmtree(date_folder, onerror=on_rm_error)
                deleted_count += 1
                total_space += folder_size
            except Exception as e:
                print(f"  [!] Could not delete {date_folder.name}: {e}")
                continue

    return deleted_count, int(total_space / (1024 * 1024))
