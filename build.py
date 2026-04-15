import os
import subprocess
import sys
import shutil
from pathlib import Path

def build():
    """
    Compiles the Job Automation Agent into a single executable.
    Usage: py build.py
    """
    print("🚀 Starting Production Build (JobBot v25.0)...")
    
    # 1. Clean previous builds
    for folder in ['build', 'dist']:
        if os.path.exists(folder):
            print(f"🧹 Cleaning {folder}...")
            shutil.rmtree(folder)
            
    # 2. PyInstaller command
    # --onefile: Bundle into a single EXE
    # --windowed: Do not open a console window (GUI only)
    # --add-data: Include templates and icons
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "JobBot_Agent",
        # Include resources (path_on_disk;path_in_exe)
        "--add-data", "templates;templates",
        "--add-data", "data/profiles;data/profiles",
        "--add-data", ".env.example;.",
        # Entry point
        "gui.py"
    ]
    
    print(f"📦 Packaging with command: {' '.join(cmd)}")
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✨ BUILD SUCCESSFUL!")
        print(f"📍 Your executable is ready at: {os.path.abspath('dist/JobBot_Agent.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Build failed: {e}")
        print("💡 Tip: Make sure you have 'pyinstaller' installed: pip install pyinstaller")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        print("Universal JobBot Builder")
        print("Commands: py build.py")
    else:
        build()
