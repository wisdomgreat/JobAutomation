"""
Job Automation System - Configuration
Loads environment variables from .env and validates required settings.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return Path(os.path.join(base_path, relative_path))

PROJECT_ROOT = resource_path(".")
load_dotenv(PROJECT_ROOT / ".env")

VERSION = "25.0.0"
GITHUB_REPO = "wisdomgreat/JobAutomation"



def _get(key: str, default: str = "") -> str:
    """Get an environment variable with optional default."""
    return os.getenv(key, default).strip()


def _require(key: str) -> str:
    """Get a required environment variable or exit with error."""
    val = os.getenv(key, "").strip()
    if not val:
        print(f"[ERROR] Missing required config: {key}")
        print(f"        Copy .env.example to .env and fill in your values.")
        sys.exit(1)
    return val


# ── Yahoo Email ──────────────────────────────────────────────
YAHOO_EMAIL = _get("YAHOO_EMAIL")
YAHOO_APP_PASSWORD = _get("YAHOO_APP_PASSWORD")

# ── LLM Provider ─────────────────────────────────────────────
LLM_PROVIDER = _get("LLM_PROVIDER", "ollama").lower()

# OpenAI
OPENAI_API_KEY = _get("OPENAI_API_KEY")
OPENAI_MODEL = _get("OPENAI_MODEL", "gpt-4o")

# Gemini
GEMINI_API_KEY = _get("GEMINI_API_KEY")
GEMINI_MODEL = _get("GEMINI_MODEL", "gemini-2.0-flash")

# Claude (Anthropic)
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = _get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

# Groq
GROQ_API_KEY = _get("GROQ_API_KEY")
GROQ_MODEL = _get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Ollama
OLLAMA_BASE_URL = _get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = _get("OLLAMA_MODEL", "llama3")

# LM Studio
LMSTUDIO_BASE_URL = _get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
LMSTUDIO_MODEL = _get("LMSTUDIO_MODEL", "local-model")

# OpenRouter
OPENROUTER_API_KEY = _get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")

# ── Job Role Filtering ───────────────────────────────────────
_roles_raw = _get("TARGET_ROLES", "")
TARGET_ROLES = [r.strip() for r in _roles_raw.split(",") if r.strip()] if _roles_raw else []
MIN_ROLE_MATCH_SCORE = int(_get("MIN_ROLE_MATCH_SCORE", "60"))
MATCH_SCORE_THRESHOLD = int(_get("MATCH_SCORE_THRESHOLD", "75"))

# ── Indeed ────────────────────────────────────────────────────
INDEED_EMAIL = _get("INDEED_EMAIL")
INDEED_PASSWORD = _get("INDEED_PASSWORD")

# ── LinkedIn ──────────────────────────────────────────────────
LINKEDIN_EMAIL = _get("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = _get("LINKEDIN_PASSWORD")

# ── General Settings ─────────────────────────────────────────
MAX_JOBS_PER_SCAN = int(_get("MAX_JOBS_PER_SCAN", "20"))
HEADLESS_BROWSER = _get("HEADLESS_BROWSER", "false").lower() == "true"
TELEMETRY_ENABLED = _get("TELEMETRY_ENABLED", "false").lower() == "true"
SUPABASE_URL = _get("SUPABASE_URL", "")
SUPABASE_KEY = _get("SUPABASE_KEY", "")
ACCOUNT_PASSWORD = _get("ACCOUNT_PASSWORD", "JobBotPass!2024") # Default for auto-account creation



# ── Paths ─────────────────────────────────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
BASE_RESUME_PDF = DATA_DIR / "base_resume.pdf"
BASE_RESUME_DOCX = DATA_DIR / "base_resume.docx"
DB_PATH = DATA_DIR / "applications.db"
PROFILE_PATH = DATA_DIR / "profile.yaml"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)


def validate():
    """Validate configuration based on what features are being used."""
    errors = []

    if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
        errors.append("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
    elif LLM_PROVIDER == "gemini" and not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is required when LLM_PROVIDER=gemini")
    elif LLM_PROVIDER == "claude" and not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY is required when LLM_PROVIDER=claude")
    elif LLM_PROVIDER == "groq" and not GROQ_API_KEY:
        errors.append("GROQ_API_KEY is required when LLM_PROVIDER=groq")
    elif LLM_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY is required when LLM_PROVIDER=openrouter")

    valid_providers = ("openai", "ollama", "lmstudio", "gemini", "claude", "groq", "openrouter")
    if LLM_PROVIDER not in valid_providers:
        errors.append(f"Invalid LLM_PROVIDER: '{LLM_PROVIDER}'. Must be one of: {', '.join(valid_providers)}")

    if errors:
        for e in errors:
            print(f"[CONFIG ERROR] {e}")
        sys.exit(1)


def summary() -> str:
    """Return a formatted summary of current configuration."""
    lines = [
        "╔══════════════════════════════════════════════╗",
        "║        Job Automation - Configuration        ║",
        "╠══════════════════════════════════════════════╣",
        f"  LLM Provider:    {LLM_PROVIDER}",
    ]
    if LLM_PROVIDER == "openai":
        lines.append(f"  OpenAI Model:    {OPENAI_MODEL}")
    elif LLM_PROVIDER == "ollama":
        lines.append(f"  Ollama Model:    {OLLAMA_MODEL}")
        lines.append(f"  Ollama URL:      {OLLAMA_BASE_URL}")
    elif LLM_PROVIDER == "lmstudio":
        lines.append(f"  LM Studio Model: {LMSTUDIO_MODEL}")
        lines.append(f"  LM Studio URL:   {LMSTUDIO_BASE_URL}")
    elif LLM_PROVIDER == "gemini":
        lines.append(f"  Gemini Model:    {GEMINI_MODEL}")
    elif LLM_PROVIDER == "claude":
        lines.append(f"  Claude Model:    {ANTHROPIC_MODEL}")
    elif LLM_PROVIDER == "groq":
        lines.append(f"  Groq Model:      {GROQ_MODEL}")
    elif LLM_PROVIDER == "openrouter":
        lines.append(f"  OpenRouter Model: {OPENROUTER_MODEL}")

    lines.append(f"  Yahoo Email:     {'✓ configured' if YAHOO_EMAIL else '✗ not set'}")
    lines.append(f"  Target Roles:    {', '.join(TARGET_ROLES) if TARGET_ROLES else 'all roles'}")
    lines.append(f"  Indeed Login:    {'✓ configured' if INDEED_EMAIL else '✗ not set'}")
    lines.append(f"  LinkedIn Login:  {'✓ configured' if LINKEDIN_EMAIL else '✗ not set'}")
    lines.append(f"  Max Jobs/Scan:   {MAX_JOBS_PER_SCAN}")
    lines.append(f"  Browser Mode:    {'headless' if HEADLESS_BROWSER else 'visible'}")
    lines.append("╚══════════════════════════════════════════════╝")
    return "\n".join(lines)
