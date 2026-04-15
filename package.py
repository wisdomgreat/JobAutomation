import os
import shutil
import subprocess
import sys
from pathlib import Path

# --- Configuration ---
APP_NAME = "SovereignAgent"
ENTRY_POINT = "gui.py"
ICON_PATH = "" # Add icon path here if you have a .ico file

# Detect CustomTkinter path
try:
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)
except ImportError:
    print("[ERROR] CustomTkinter not found. Please install it first.")
    sys.exit(1)

# List of folders to include
DATA_FOLDERS = [
    ("data", "data"),
    ("templates", "templates"),
    (ctk_path, "customtkinter"),
]

# List of files/folders to EXCLUDE from the build (Secrets)
EXCLUDES = [
    ".env",
    "applications.db", # We'll ship an empty data folder instead
    "__pycache__",
    ".git",
    "output",
    "logs"
]

def build():
    print(f"🚀 Starting Build: {APP_NAME}")
    
    # 1. Cleanup previous builds
    cur_dir = Path(__file__).parent
    build_dir = cur_dir / "build"
    dist_dir = cur_dir / "dist"
    
    if build_dir.exists(): shutil.rmtree(build_dir)
    if dist_dir.exists(): shutil.rmtree(dist_dir)
    
    # 2. Construct PyInstaller command
    # Use system-specific separator for --add-data (; for Windows, : for Unix)
    sep = ";" if os.name == "nt" else ":"
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        f"--name={APP_NAME}",
    ]
    
    # Add data folders
    for src, dst in DATA_FOLDERS:
        cmd.extend(["--add-data", f"{src}{sep}{dst}"])
        
    # Exclude modules we don't need to reduce size
    cmd.extend(["--exclude-module", "pytest"])
    cmd.extend(["--exclude-module", "unittest"])

    cmd.append(ENTRY_POINT)
    
    print(f"📦 Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print(f"\n✅ Build Complete! Your standalone app is in: {dist_dir}")
        print(f"   Note: Ensure you include a '.env.example' file in the distribution.")
    else:
        print(f"\n❌ Build Failed with exit code: {result.returncode}")

if __name__ == "__main__":
    build()
