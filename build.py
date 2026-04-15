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

# --- Configuration ---
APP_NAME = "SovereignAgent"
ENTRY_POINT = "gui.py"
ICON_PATH = "image/favicon.ico"

def build():
    safe_print(f"🚀 Starting Production Build: {APP_NAME}")
    
    # 1. Detect CustomTkinter path for assets (themes/json)
    try:
        import customtkinter
        ctk_path = os.path.dirname(customtkinter.__file__)
        safe_print(f"📍 Found CustomTkinter at: {ctk_path}")
    except ImportError:
        safe_print("❌ ERROR: CustomTkinter not found. Please install it: pip install customtkinter")
        sys.exit(1)

    # 2. Cleanup previous builds
    cur_dir = Path(__file__).parent
    build_dir = cur_dir / "build"
    dist_dir = cur_dir / "dist"
    
    if build_dir.exists(): 
        safe_print("🧹 Cleaning build directory...")
        shutil.rmtree(build_dir)
    if dist_dir.exists(): 
        safe_print("🧹 Cleaning dist directory...")
        shutil.rmtree(dist_dir)
    
    # 3. Construct PyInstaller command
    # Use system-specific separator for --add-data (; for Windows, : for Unix)
    sep = ";" if os.name == "nt" else ":"
    
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", APP_NAME,
    ]
    
    # Add Icon if exists
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])
        safe_print(f"🎨 Including Icon: {ICON_PATH}")

    # Data folders to bundle
    data_to_add = [
        ("templates", "templates"),
        ("image", "image"),
        ("data", "data"),
        (ctk_path, "customtkinter"),
        (".env.example", "."),
    ]
    
    for src, dst in data_to_add:
        if os.path.exists(src):
            cmd.extend(["--add-data", f"{src}{sep}{dst}"])
            safe_print(f"📁 Adding Data: {src} -> {dst}")

    # Exclude heavy modules to reduce size
    module_excludes = [
        "pandas", "numpy", "matplotlib", "scipy", "notebook", 
        "IPython", "jedi", "pyarrow", "pytest",
        "tkinter.test", "sqlite3.test"
    ]
    for mod in module_excludes:
        cmd.extend(["--exclude-module", mod])

    cmd.append(ENTRY_POINT)
    
    safe_print(f"📦 Executing Build Command...")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        # Move final exe if named differently by default
        exe_path = dist_dir / f"{APP_NAME}.exe"
        safe_print(f"\n✨ BUILD SUCCESSFUL!")
        safe_print(f"📍 Standalone executable: {exe_path.absolute()}")
        safe_print(f"💡 Note: Configuration requires a valid .env (use .env.example as template)")
    else:
        safe_print(f"\n❌ Build Failed with exit code: {result.returncode}")

if __name__ == "__main__":
    build()
