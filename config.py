"""
Job Automation System - Configuration
Loads environment variables from .env and validates required settings.
"""

import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv, set_key

# 1. Base Paths
def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return Path(os.path.join(base_path, relative_path))

# PROJECT_ROOT is where the software lives (Program Files)
PROJECT_ROOT = get_resource_path(".")

# 2. PRO-PERSISTENCE: Where the data lives (Permanent Storage)
# Standard Windows path: %APPDATA%\TDWAS\SovereignAgent
if os.name == "nt":
    BASE_DATA_PATH = Path(os.getenv("APPDATA")) / "TDWAS" / "SovereignAgent"
else:
    BASE_DATA_PATH = Path.home() / ".sovereign_agent"

DATA_DIR = BASE_DATA_PATH / "data"
LOG_DIR = BASE_DATA_PATH / "logs"
SCRATCH_DIR = BASE_DATA_PATH / "scratch"
ENV_PATH = BASE_DATA_PATH / ".env"

# Ensure permanent folders exist
BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# 3. MIGRATION ENGINE: Copy data from temp/local to permanent
def run_migration():
    local_data = Path("data")
    if local_data.exists() and not (DATA_DIR / "applications.db").exists():
        print(f"[System] Professional Upgrade: Migrating legacy data to permanent storage...")
        try:
            for item in local_data.glob("*"):
                if item.is_file():
                    shutil.copy2(item, DATA_DIR / item.name)
                elif item.is_dir():
                    shutil.copytree(item, DATA_DIR / item.name, dirs_exist_ok=True)
            
            # Copy .env if exists
            local_env = Path(".env")
            if local_env.exists():
                shutil.copy2(local_env, ENV_PATH)
            
            print("[System] Migration successful. Data is now persistent.")
        except Exception as e:
            print(f"[Warning] Migration partially failed: {e}")

run_migration()

# 4. Load Configuration
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # Initialize a clean .env from example if it doesn't exist
    example_env = PROJECT_ROOT / ".env.example"
    if example_env.exists():
        shutil.copy2(example_env, ENV_PATH)
    load_dotenv(ENV_PATH)

VERSION = "26.6.4"
GITHUB_REPO = "wisdomgreat/JobAutomation"

def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()

# --- Config Variables ---
YAHOO_EMAIL = _get("YAHOO_EMAIL")
YAHOO_APP_PASSWORD = _get("YAHOO_APP_PASSWORD")
LLM_PROVIDER = _get("LLM_PROVIDER", "ollama").lower()
OPENAI_API_KEY = _get("OPENAI_API_KEY")
OPENAI_MODEL = _get("OPENAI_MODEL", "gpt-4o")
GEMINI_API_KEY = _get("GEMINI_API_KEY")
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-2.0-flash")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
GROQ_API_KEY = _get("GROQ_API_KEY")
GROQ_MODEL = _get("GROQ_MODEL", "llama-3.3-70b-versatile")
OLLAMA_BASE_URL = _get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = _get("OLLAMA_MODEL", "llama3")
LMSTUDIO_BASE_URL = _get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = _get("LMSTUDIO_MODEL", "local-model")
OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

_roles_raw = _get("TARGET_ROLES", "")
TARGET_ROLES = [r.strip() for r in _roles_raw.split(",") if r.strip()] if _roles_raw else []
MIN_ROLE_MATCH_SCORE = int(_get("MIN_ROLE_MATCH_SCORE", "60"))
MATCH_SCORE_THRESHOLD = int(_get("MATCH_SCORE_THRESHOLD", "75"))

INDEED_EMAIL = _get("INDEED_EMAIL")
INDEED_PASSWORD = _get("INDEED_PASSWORD")
LINKEDIN_EMAIL = _get("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = _get("LINKEDIN_PASSWORD")

MAX_JOBS_PER_SCAN = int(_get("MAX_JOBS_PER_SCAN", "20"))
HEADLESS_BROWSER = _get("HEADLESS_BROWSER", "false").lower() == "true"
TELEMETRY_ENABLED = _get("TELEMETRY_ENABLED", "false").lower() == "true"
ACCOUNT_PASSWORD = _get("ACCOUNT_PASSWORD", "JobBotPass!2024")

# Paths (PRO-PERSISTENT)
OUTPUT_DIR = BASE_DATA_PATH / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates" # Templates stay with the app
BASE_RESUME_PDF = DATA_DIR / "base_resume.pdf"
BASE_RESUME_DOCX = DATA_DIR / "base_resume.docx"
DB_PATH = DATA_DIR / "applications.db"
PROFILE_PATH = DATA_DIR / "profile.yaml"

OUTPUT_DIR.mkdir(exist_ok=True)

def validate():
    valid_providers = ("openai", "ollama", "lmstudio", "gemini", "claude", "groq", "openrouter")
    if LLM_PROVIDER not in valid_providers:
        print(f"[CONFIG ERROR] Invalid provider: {LLM_PROVIDER}")
        return False
    return True

def summary() -> str:
    # (Existing summary logic...)
    return f"Sovereign Agent v{VERSION} | Data: {DATA_DIR}"
