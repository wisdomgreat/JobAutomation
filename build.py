import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import customtkinter
except ImportError:
    customtkinter = None

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

def run_pyinstaller(mode_flag, name, extra_args=None):
    """Executes PyInstaller with given parameters."""
    sep = ";" if os.name == "nt" else ":"
    ctk_path = os.path.dirname(customtkinter.__file__) if 'customtkinter' in sys.modules else ""
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", mode_flag, "--windowed",
        "--name", name, "--clean", "--noupx"
    ]
    
    if os.path.exists(VERSION_FILE) and os.name == "nt":
        cmd.extend(["--version-file", VERSION_FILE])
    
    if os.path.exists(ICON_PATH):
        cmd.extend(["--icon", ICON_PATH])

    # Core Assets
    data_to_add = [
        ("templates", "templates"),
        ("image", "image"),
        ("VERSION", "."),
        (ctk_path, "customtkinter"),
        (".env.example", "."),
    ]
    
    if ctk_path and not os.path.exists("customtkinter"):
        safe_print(f"📂 Copying customtkinter assets from {ctk_path}...")
        try:
            shutil.copytree(ctk_path, "customtkinter", dirs_exist_ok=True)
        except Exception as e:
            safe_print(f"⚠️ Warning: Could not copy customtkinter: {e}")
    
    for src, dst in data_to_add:
        if src and os.path.exists(src):
            cmd.extend(["--add-data", f"{src}{sep}{dst}"])

    # Aggressive Module Exclusions
    module_excludes = [
        "PySide6", "PyQt6", "PyQt5", "tkinter.test", 
        "pandas", "numpy", "matplotlib", "scipy", "notebook", "IPython", "jedi", "pyarrow", "tables", "PIL.ImageQt",
        "pytest", "tox", "nose", "pydoc", "pydoc_data", "email.testsuite", "sqlite3.test", "test", "tests"
    ]
    for mod in module_excludes:
        cmd.extend(["--exclude-module", mod])

    if extra_args:
        cmd.extend(extra_args)

    cmd.append(ENTRY_POINT)
    safe_print(f"\n📦 Building {name} ({mode_flag.upper()})...")
    safe_print(f"DEBUG: Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        safe_print(f"❌ PyInstaller Error for {name}:")
        safe_print(result.stdout)
        safe_print(result.stderr)
        return False
    return True

def build():
    safe_print(f"🚀 [TDWAS Pro] Starting Universal Production Build: {APP_NAME}")
    
    # 1. Environment Check
    if customtkinter is None:
        safe_print("❌ ERROR: CustomTkinter not found.")
        sys.exit(1)

    # 2. Cleanup
    cur_dir = Path(__file__).parent
    build_dir = cur_dir / "build"
    dist_dir = cur_dir / "dist"
    
    try:
        if build_dir.exists(): shutil.rmtree(build_dir, ignore_errors=True)
        if dist_dir.exists(): shutil.rmtree(dist_dir, ignore_errors=True) 
        safe_print("🧹 Workspace Sanitized")
    except Exception as e:
        safe_print(f"⚠️ Warning: Could not clean build folders: {e}")
    
    # 3. BUILD 1: Portable Version (ONEFILE - Single EXE)
    # Using a slightly different name to avoid collision in dist/
    portable_name = f"{APP_NAME}_Portable"
    if run_pyinstaller("--onefile", portable_name):
        safe_print(f"✅ Portable Build Complete: dist/{portable_name}.exe")
    else:
        safe_print("❌ Portable Build Failed.")
        sys.exit(1)

    # 4. BUILD 2: Debug Version (OneFile + Console)
    debug_name = f"{APP_NAME}_Debug"
    if run_pyinstaller("--onefile", debug_name, extra_args=["--console"]):
        safe_print(f"✅ Debug Build Complete: dist/{debug_name}.exe")
    else:
        safe_print("❌ Debug Build Failed.")

    # 5. BUILD 3: Installer Source (OneDir)
    if run_pyinstaller("--onedir", APP_NAME):
        safe_print(f"✅ Installer Assets Complete: dist/{APP_NAME}/")
    else:
        safe_print("❌ Installer Assets Build Failed.")
        sys.exit(1)

    # 6. TRIGGER INNO SETUP (Optional)
    iss_file = cur_dir / "SovereignInstaller.iss"
    if iss_file.exists() and os.name == "nt":
        safe_print("\n🔨 Attempting to compile Installer (Inno Setup)...")
        # Common ISCC paths
        iscc_paths = [
            r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
            r"C:\Program Files\Inno Setup 6\ISCC.exe",
            "ISCC.exe" # If in PATH
        ]
        
        iscc_found = False
        iscc_cmd = None
        for path in iscc_paths:
            try:
                subprocess.run([path, "/?"], capture_output=True)
                iscc_cmd = path
                iscc_found = True
                break
            except Exception: continue
        
        if iscc_found:
            safe_print(f"📍 Found Inno Setup Compiler: {iscc_cmd}")
            res = subprocess.run([iscc_cmd, str(iss_file)])
            if res.returncode == 0:
                safe_print("✨ SUCCESS: Installer created in dist/")
            else:
                safe_print("⚠️ Inno Setup failed to compile.")
        else:
            safe_print("ℹ️ ISCC.exe not found in standard paths. Please compile SovereignInstaller.iss manually.")

if __name__ == "__main__":
    build()
