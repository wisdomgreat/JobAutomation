"""
Job Automation System - Configuration
Loads environment variables from .env and validates required settings.
"""

import os
import sys
import shutil
import re
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

PROJECT_ROOT = get_resource_path(".")

if os.name == "nt":
    BASE_DATA_PATH = Path(os.getenv("APPDATA")) / "TDWAS" / "SovereignAgent"
else:
    BASE_DATA_PATH = Path.home() / ".sovereign_agent"

DATA_DIR = BASE_DATA_PATH / "data"
LOG_DIR = BASE_DATA_PATH / "logs"
SCRATCH_DIR = BASE_DATA_PATH / "scratch"
ENV_PATH = BASE_DATA_PATH / ".env"

BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)

# 2. Configuration Engine
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)
else:
    example_env = PROJECT_ROOT / ".env.example"
    if example_env.exists():
        shutil.copy2(example_env, ENV_PATH)
    load_dotenv(ENV_PATH, override=True)

def _get_version() -> str:
    try:
        v_file = PROJECT_ROOT / "VERSION"
        if v_file.exists():
            return v_file.read_text().strip()
    except Exception:
        pass
    return "30.6.0"

VERSION = _get_version()
GITHUB_REPO = "wisdomgreat/JobAutomation"

def _get(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()

def reload_from_env():
    """Phase 25.0: Dynamic configuration reloading engine."""
    if ENV_PATH.exists():
        load_dotenv(ENV_PATH, override=True)
    
    global YAHOO_EMAIL, YAHOO_APP_PASSWORD, LLM_PROVIDER, IMAP_SERVER, IMAP_PORT
    global TARGET_ROLES, MATCH_SCORE_THRESHOLD, MIN_ROLE_MATCH_SCORE
    global DAYS_BACK, MAX_JOBS_PER_SCAN, HEADLESS_BROWSER, STEALTH_MODE
    global OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY

    YAHOO_EMAIL = _get("YAHOO_EMAIL")
    YAHOO_APP_PASSWORD = _get("YAHOO_APP_PASSWORD")
    
    # Universal IMAP Auto-detection (Phase 30.6)
    IMAP_SERVER = _get("IMAP_SERVER")
    IMAP_PORT = int(_get("IMAP_PORT", "993"))
    
    if not IMAP_SERVER and YAHOO_EMAIL:
        domain = YAHOO_EMAIL.split("@")[-1].lower()
        if "gmail.com" in domain: IMAP_SERVER = "imap.gmail.com"
        elif "outlook.com" in domain or "hotmail.com" in domain: IMAP_SERVER = "outlook.office365.com"
        elif "yahoo.com" in domain: IMAP_SERVER = "imap.mail.yahoo.com"
        elif "icloud.com" in domain: IMAP_SERVER = "imap.mail.me.com"
        else: IMAP_SERVER = "imap.mail.yahoo.com"

    LLM_PROVIDER = _get("LLM_PROVIDER", "claude").lower()
    
    _roles_raw = _get("TARGET_ROLES", "")
    TARGET_ROLES = [r.strip() for r in _roles_raw.split(",") if r.strip()] if _roles_raw else []
    
    MATCH_SCORE_THRESHOLD = int(_get("MATCH_SCORE_THRESHOLD", "60"))
    MIN_ROLE_MATCH_SCORE = int(_get("MIN_ROLE_MATCH_SCORE", "60"))
    
    DAYS_BACK = float(_get("DAYS_BACK", "7.0"))
    MAX_JOBS_PER_SCAN = int(_get("MAX_JOBS_PER_SCAN", "20"))
    HEADLESS_BROWSER = _get("HEADLESS_BROWSER", "false").lower() == "true"
    STEALTH_MODE = _get("STEALTH_MODE", "true").lower() == "true"

# --- Globals ---
YAHOO_EMAIL = _get("YAHOO_EMAIL")
YAHOO_APP_PASSWORD = _get("YAHOO_APP_PASSWORD")
IMAP_SERVER = _get("IMAP_SERVER")
IMAP_PORT = int(_get("IMAP_PORT", "993"))

if not IMAP_SERVER and YAHOO_EMAIL:
    domain = YAHOO_EMAIL.split("@")[-1].lower()
    if "gmail.com" in domain: IMAP_SERVER = "imap.gmail.com"
    elif "outlook.com" in domain or "hotmail.com" in domain: IMAP_SERVER = "outlook.office365.com"
    elif "yahoo.com" in domain: IMAP_SERVER = "imap.mail.yahoo.com"
    elif "icloud.com" in domain: IMAP_SERVER = "imap.mail.me.com"
    else: IMAP_SERVER = "imap.mail.yahoo.com"

LLM_PROVIDER = _get("LLM_PROVIDER", "ollama").lower()
OPENAI_API_KEY = _get("OPENAI_API_KEY")
OPENAI_MODEL = _get("OPENAI_MODEL", "gpt-4o")
GEMINI_API_KEY = _get("GEMINI_API_KEY")
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-2.0-flash")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
GROQ_API_KEY = _get("GROQ_API_KEY")
GROQ_MODEL = _get("GROQ_MODEL", "llama-3.3-70b-versatile")
OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

_roles_raw = _get("TARGET_ROLES", "")
TARGET_ROLES = [r.strip() for r in _roles_raw.split(",") if r.strip()] if _roles_raw else []
MATCH_SCORE_THRESHOLD = int(_get("MATCH_SCORE_THRESHOLD", "60"))
MIN_ROLE_MATCH_SCORE = int(_get("MIN_ROLE_MATCH_SCORE", "60"))

# Neural Acronym Map (Expansion Core)
ACRONYM_MAP = {
    "it": "Information Technology",
    "cs": "Customer Service",
    "swe": "Software Engineer",
    "dev": "Developer",
    "qa": "Quality Assurance",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "cyber": "Cybersecurity",
    "hr": "Human Resources"
}

DAYS_BACK = float(_get("DAYS_BACK", "7.0"))
MAX_JOBS_PER_SCAN = int(_get("MAX_JOBS_PER_SCAN", "20"))
HEADLESS_BROWSER = _get("HEADLESS_BROWSER", "false").lower() == "true"
STEALTH_MODE = _get("STEALTH_MODE", "true").lower() == "true"

# Paths
OUTPUT_DIR = BASE_DATA_PATH / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
BASE_RESUME_PDF = DATA_DIR / "base_resume.pdf"
BASE_RESUME_DOCX = DATA_DIR / "base_resume.docx"
DB_PATH = DATA_DIR / "applications.db"
PROFILE_PATH = DATA_DIR / "profile.yaml"

OUTPUT_DIR.mkdir(exist_ok=True)

def validate():
    valid_providers = ("openai", "ollama", "lmstudio", "gemini", "claude", "groq", "openrouter")
    return LLM_PROVIDER in valid_providers

def summary() -> str:
    return f"Sovereign Agent v{VERSION} | Core: {IMAP_SERVER} | Discovery: {len(TARGET_ROLES)} roles"
