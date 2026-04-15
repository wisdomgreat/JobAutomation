import os
import shutil
import subprocess
import sys
from pathlib import Path

def safe_print(msg):
    """Print that handles Windows console encoding issues."""
    try:
        print(msg)
    except UnicodeEncodeError:
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding:
            encoded = msg.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
            print(encoded)
        else:
            print(msg.encode('ascii', errors='ignore').decode('ascii'))

# --- TDWAS Technology Configuration ---
APP_NAME = "SovereignAgent"
ENTRY_POINT = "gui.py"
ICON_PATH = "image/favicon.ico"
PUBLISHER = "TDWAS Technology"
VERSION_FILE = "file_version_info.txt"

def build():
    safe_print(f"🚀 [TDWAS Pro] Starting Production Build: {APP_NAME}")
    
    # 1. Detect CustomTkinter path for assets
    try:
        import customtkinter
        ctk_path = os.path.dirname(customtkinter.__file__)
        safe_print(f"📍 Found CustomTkinter at: {ctk_path}")
    except ImportError:
        safe_print("❌ ERROR: CustomTkinter not found. Install: pip install customtkinter")
        sys.exit(1)

    # 2. Cleanup
    cur_dir = Path(__file__).parent
    build_dir = cur_dir / "build"
    dist_dir = cur_dir / "dist"
    
    try:
        if build_dir.exists(): shutil.rmtree(build_dir, ignore_errors=True)
        if dist_dir.exists(): shutil.rmtree(dist_dir, ignore_errors=True)
        safe_print("🧹 Workspace Sanitized (Clean Build)")
    except Exception as e:
        safe_print(f"⚠️ Warning: Could not clean build folders: {e}")
    
    # 3. Construct PyInstaller command
    sep = ";" if os.name == "nt" else ":"
    
    # Mode Toggle: OneDir is standard for Setup.exe installers
    mode = "--onedir" 
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        mode,
        "--windowed",
        "--name", APP_NAME,
        "--clean",
    ]
    
    # Add TDWAS Metadata (Windows Only)
    if os.path.exists(VERSION_FILE) and os.name == "nt":
        cmd.extend(["--version-file", VERSION_FILE])
        safe_print(f"🏷️ Embedding TDWAS Metadata: {VERSION_FILE}")

    # Add Icon
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    # Core Assets
    data_to_add = [
        ("templates", "templates"),
        ("image", "image"),
        (ctk_path, "customtkinter"),
        (".env.example", "."),
    ]
    
    for src, dst in data_to_add:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src}{sep}{dst}"])

    # Aggressive Module Exclusions (Optimized for Lean Pro Distribution)
    module_excludes = [
        # Heavy Graphics/UI
        "PySide6", "PyQt6", "PyQt5", "tkinter.test", 
        # Data Science (Large Bloat)
        "pandas", "numpy", "matplotlib", "scipy", "notebook", "IPython", "jedi", "pyarrow", "tables", "PIL.ImageQt",
        # Dev tools & Unused Standard Libs
        "pytest", "tox", "nose", "pydoc", "pydoc_data", "email.testsuite", "sqlite3.test", "test", "tests"
    ]
    for mod in module_excludes:
        cmd.extend(["--exclude-module", mod])

    cmd.append(ENTRY_POINT)
    
    safe_print(f"📦 Packaging Architecture: PROFESSIONAL ({mode.replace('--', '').upper()})")
    safe_print(f"📦 Optimized Slimming: Excluded {len(module_excludes)} redundant libraries.")
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        safe_print(f"\n✨ [TDWAS Pro] BUILD SUCCESSFUL!")
        target = dist_dir / f"{APP_NAME}.exe"
        safe_print(f"📍 Export Location: {target.absolute()}")
    else:
        safe_print(f"\n❌ Build Failed with exit code: {result.returncode}")

if __name__ == "__main__":
    build()
