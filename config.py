import os
from pathlib import Path
from dotenv import load_dotenv, set_key

# --- Multi-Platform Path Resolution ---
ENV_PATH = Path(".env")
if not ENV_PATH.exists():
    ENV_PATH = Path(os.getenv("APPDATA", "")) / "TDWAS" / "SovereignAgent" / ".env"
    ENV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not ENV_PATH.exists():
        # Fallback to current directory for first-time setup or dev
        ENV_PATH = Path(".env")

# Always load environment
load_dotenv(str(ENV_PATH))

def _get(key, default=""):
    return os.getenv(key, default)

def reload_from_env():
    """Hot-reload configuration from the .env file."""
    load_dotenv(str(ENV_PATH), override=True)
    global YAHOO_EMAIL, YAHOO_APP_PASSWORD, OUTLOOK_EMAIL, OUTLOOK_APP_PASSWORD
    global GMAIL_EMAIL, GMAIL_APP_PASSWORD, TARGET_ROLES, MATCH_SCORE_THRESHOLD, MIN_ROLE_MATCH_SCORE
    global DAYS_BACK, MAX_JOBS_PER_SCAN, HEADLESS_BROWSER, STEALTH_MODE
    global IMAP_SERVER, IMAP_PORT, ACRONYM_MAP, DISCOVERY_FOLDERS, DEEP_SEARCH
    global GUI_APPEARANCE_MODE, GUI_ACCENT_COLOR, GUI_COLOR_THEME
    global OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY
    global OLLAMA_BASE_URL, LMSTUDIO_BASE_URL, OLLAMA_MODEL, LMSTUDIO_MODEL
    global LINKEDIN_EMAIL, LINKEDIN_PASSWORD, INDEED_EMAIL, INDEED_PASSWORD
    global ZIPRECRUITER_EMAIL, ZIPRECRUITER_PASSWORD, GLASSDOOR_EMAIL, GLASSDOOR_PASSWORD

    YAHOO_EMAIL = _get("YAHOO_EMAIL")
    YAHOO_APP_PASSWORD = _get("YAHOO_APP_PASSWORD")
    OUTLOOK_EMAIL = _get("OUTLOOK_EMAIL")
    OUTLOOK_APP_PASSWORD = _get("OUTLOOK_APP_PASSWORD")
    GMAIL_EMAIL = _get("GMAIL_EMAIL")
    GMAIL_APP_PASSWORD = _get("GMAIL_APP_PASSWORD")
    
    TARGET_ROLES = _get("TARGET_ROLES", "Software Engineer, Python Developer")
    MATCH_SCORE_THRESHOLD = int(_get("MATCH_SCORE_THRESHOLD", "70"))
    MIN_ROLE_MATCH_SCORE = int(_get("MIN_ROLE_MATCH_SCORE", "30"))
    DAYS_BACK = int(_get("DAYS_BACK", "3"))
    MAX_JOBS_PER_SCAN = int(_get("MAX_JOBS_PER_SCAN", "50"))
    HEADLESS_BROWSER = _get("HEADLESS_BROWSER", "false").lower() == "true"
    STEALTH_MODE = _get("STEALTH_MODE", "true").lower() == "true"
    
    IMAP_SERVER = _get("IMAP_SERVER", "imap.mail.yahoo.com")
    IMAP_PORT = int(_get("IMAP_PORT", "993"))
    ACRONYM_MAP = _get("ACRONYM_MAP", "SWE: Software Engineer, QA: Quality Assurance")
    DEEP_SEARCH = _get("DEEP_SEARCH", "false").lower() == "true"
    
    _folders_raw = _get("DISCOVERY_FOLDERS", "INBOX,Indeed,Jobs,LinkedIn,Bulk,canada job application,urgentapply")
    DISCOVERY_FOLDERS = [f.strip() for f in _folders_raw.split(",") if f.strip()]
    
    GUI_APPEARANCE_MODE = _get("GUI_APPEARANCE_MODE", "Dark")
    GUI_COLOR_THEME = _get("GUI_COLOR_THEME", "blue")
    GUI_ACCENT_COLOR = _get("GUI_ACCENT_COLOR", "#00d4ff")

    # LLM Providers
    OLLAMA_BASE_URL = _get("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = _get("OLLAMA_MODEL", "llama3")
    LMSTUDIO_BASE_URL = _get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    LMSTUDIO_MODEL = _get("LMSTUDIO_MODEL", "local-model")

    # Job Platforms
    LINKEDIN_EMAIL = _get("LINKEDIN_EMAIL")
    LINKEDIN_PASSWORD = _get("LINKEDIN_PASSWORD")
    INDEED_EMAIL = _get("INDEED_EMAIL")
    INDEED_PASSWORD = _get("INDEED_PASSWORD")
    ZIPRECRUITER_EMAIL = _get("ZIPRECRUITER_EMAIL")
    ZIPRECRUITER_PASSWORD = _get("ZIPRECRUITER_PASSWORD")
    GLASSDOOR_EMAIL = _get("GLASSDOOR_EMAIL")
    GLASSDOOR_PASSWORD = _get("GLASSDOOR_PASSWORD")

# --- Globals ---
YAHOO_EMAIL = _get("YAHOO_EMAIL")
YAHOO_APP_PASSWORD = _get("YAHOO_APP_PASSWORD")
OUTLOOK_EMAIL = _get("OUTLOOK_EMAIL")
OUTLOOK_APP_PASSWORD = _get("OUTLOOK_APP_PASSWORD")
GMAIL_EMAIL = _get("GMAIL_EMAIL")
GMAIL_APP_PASSWORD = _get("GMAIL_APP_PASSWORD")

TARGET_ROLES = _get("TARGET_ROLES", "Software Engineer, Python Developer")
MATCH_SCORE_THRESHOLD = int(_get("MATCH_SCORE_THRESHOLD", "70"))
MIN_ROLE_MATCH_SCORE = int(_get("MIN_ROLE_MATCH_SCORE", "30"))
DAYS_BACK = int(_get("DAYS_BACK", "3"))
MAX_JOBS_PER_SCAN = int(_get("MAX_JOBS_PER_SCAN", "50"))
HEADLESS_BROWSER = _get("HEADLESS_BROWSER", "false").lower() == "true"
STEALTH_MODE = _get("STEALTH_MODE", "true").lower() == "true"
BROWSER_ENGINE = _get("BROWSER_ENGINE", "selenium") # selenium or playwright

IMAP_SERVER = _get("IMAP_SERVER", "imap.mail.yahoo.com")
IMAP_PORT = int(_get("IMAP_PORT", "993"))
ACRONYM_MAP = _get("ACRONYM_MAP", "SWE: Software Engineer, QA: Quality Assurance")

# Intelligence Core Constants
DEEP_SEARCH = _get("DEEP_SEARCH", "false").lower() == "true"
AX_TREE_LIMIT = int(_get("AX_TREE_LIMIT", "50"))

# AI Providers
OPENAI_API_KEY = _get("OPENAI_API_KEY")
OPENAI_MODEL = _get("OPENAI_MODEL", "gpt-4o")
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
GEMINI_API_KEY = _get("GEMINI_API_KEY")
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-1.5-pro")
OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

# Local LLM Defaults
OLLAMA_BASE_URL = _get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = _get("OLLAMA_MODEL", "llama3")
LMSTUDIO_BASE_URL = _get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = _get("LMSTUDIO_MODEL", "local-model")

# Job Board Credentials
LINKEDIN_EMAIL = _get("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = _get("LINKEDIN_PASSWORD")
INDEED_EMAIL = _get("INDEED_EMAIL")
INDEED_PASSWORD = _get("INDEED_PASSWORD")
ZIPRECRUITER_EMAIL = _get("ZIPRECRUITER_EMAIL")
ZIPRECRUITER_PASSWORD = _get("ZIPRECRUITER_PASSWORD")
GLASSDOOR_EMAIL = _get("GLASSDOOR_EMAIL")
GLASSDOOR_PASSWORD = _get("GLASSDOOR_PASSWORD")

# GUI Configuration
GUI_APPEARANCE_MODE = _get("GUI_APPEARANCE_MODE", "Dark")
GUI_COLOR_THEME = _get("GUI_COLOR_THEME", "blue")
GUI_ACCENT_COLOR = _get("GUI_ACCENT_COLOR", "#00d4ff")

_folders_raw = _get("DISCOVERY_FOLDERS", "INBOX,Indeed,Jobs,LinkedIn,Bulk,canada job application,urgentapply")
DISCOVERY_FOLDERS = [f.strip() for f in _folders_raw.split(",") if f.strip()]

# Paths
BASE_DATA_PATH = Path(os.getenv("APPDATA", "")) / "TDWAS" / "SovereignAgent"
if not BASE_DATA_PATH.exists():
    BASE_DATA_PATH = Path("data")

DATA_DIR = BASE_DATA_PATH / "database"
LOG_DIR = BASE_DATA_PATH / "logs"
RESUME_DIR = BASE_DATA_PATH / "resumes"
OUTPUT_DIR = BASE_DATA_PATH / "output"

for d in [DATA_DIR, LOG_DIR, RESUME_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)
