import os
import sys
import yaml
import json
from pathlib import Path

# Add project root to path if running directly
sys.path.append(str(Path(__file__).parent.parent))

from rich.console import Console
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
import config
from dotenv import set_key
from src.llm_provider import get_llm

console = Console()

PROFILE_PATH = Path("data/profile.yaml")

class ApplicantProfile:
    """Manages the applicant profile stored in YAML."""

    def __init__(self, profile_path: Path = PROFILE_PATH):
        self.profile_path = profile_path
        self.data = self._load_default()
        if self.profile_path.exists():
            self.load()

    def _load_default(self):
        """Default profile structure."""
        return {
            "personal": {
                "first_name": "",
                "middle_name": "",
                "last_name": "",
                "preferred_name": "",
                "email": "",
                "phone": "",
                "phone_prefix": "1",
                "phone_type": "Mobile",
                "address": "",
                "address_2": "",
                "city": "",
                "province": "",
                "postal_code": "",
                "country": "Canada",
                "linkedin_url": "",
                "github_url": "",
                "portfolio_url": "",
                "twitter_url": "",
            },
            "work_authorization": {
                "authorized_to_work": True,
                "sponsorship_needed": False,
                "work_permit_type": "None",
            },
            "preferences": {
                "willing_to_relocate": True,
                "salary_expectation": "Open to discussion",
                "salary_range": "",
                "notice_period": "Immediately",
                "start_date": "Immediately",
                "work_type": "Full-time",
                "remote_preference": "Remote",
                "travel_percent": "0%",
                "preferred_industries": "",
            },
            "experience": {
                "total_years": 0.0,
                "current_title": "",
                "summary": "",
                "top_skills": "",
            },
            "education": {
                "highest_degree": "Bachelor's",
                "entries": [],
            },
            "skills": {
                "technical": "",
                "soft": "",
            },
            "languages": {
                "primary": "English",
                "others": "",
            },
            "professional": {
                "security_clearance": "None",
                "referred_by": "",
            },
            "demographics": {
                "gender": "Decline to self-identify",
                "ethnicity": "Decline to self-identify",
                "veteran": "No",
                "disability": "No",
            }
        }



    def load(self):
        """Load profile from disk."""
        try:
            with open(self.profile_path, "r") as f:
                self.data = yaml.safe_load(f) or self._load_default()
        except Exception as e:
            console.print(f"[red]Error loading profile: {e}[/]")

    def save(self):
        """Save profile to disk."""
        self.profile_path.parent.mkdir(exist_ok=True)
        try:
            with open(self.profile_path, "w") as f:
                yaml.safe_dump(self.data, f, sort_keys=False)
        except Exception as e:
            console.print(f"[red]Error saving profile: {e}[/]")

    def get_form_data(self) -> dict:
        """Flatten profile for form filling."""
        flat = {}
        for section, fields in self.data.items():
            if isinstance(fields, dict):
                for k, v in fields.items():
                    if k == "entries" and isinstance(v, list):
                        continue # handle lists separately if needed
                    flat[k] = v
        return flat

    def import_from_resume(self, resume_path: Path):
        """Extract profile data from a resume file using LLM."""
        from src.resume_builder import parse_resume # lazy import
        
        console.print(f"\n[bold cyan]🔍 Analyzing resume: {resume_path.name}...[/]")
        try:
            resume_text = parse_resume(resume_path)
            llm = get_llm()
            
            # Supercharged extraction prompt
            prompt = f"""
            Extract the applicant's professional details from the following resume text.
            Return ONLY a JSON object that strictly matches this structure. Be precise and concise.
            
            Schema:
            {{
                "personal": {{
                    "first_name": "...", "last_name": "...", "email": "...", "phone": "...",
                    "city": "...", "province": "...", "country": "...", 
                    "linkedin_url": "...", "github_url": "...", "portfolio_url": "..."
                }},
                "experience": {{
                    "total_years": 0.0, 
                    "current_title": "...", 
                    "summary": "A 1-2 sentence professional summary for profile bios",
                    "top_skills": "comma-separated list of top 5 keywords"
                }},
                "education": {{
                    "highest_degree": "..."
                }},
                "preferences": {{
                    "notice_period": "Immediately or X weeks",
                    "remote_preference": "Remote/Hybrid/Onsite"
                }},
                "skills": {{
                    "technical": "comma-separated list of tools/languages/tech stack",
                    "soft": "comma-separated soft skills"
                }}
            }}

            Resume Text:
            {resume_text[:5000]}
            """
            
            response = llm.generate(prompt, "You are a precise data extraction tool. Return ONLY JSON.").strip()
            
            # Clean up potential markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
                
            extracted = json.loads(response)
            
            # Merge extracted data into current profile
            for section, fields in extracted.items():
                if section in self.data and isinstance(fields, dict):
                    for k, v in fields.items():
                        if v: self.data[section][k] = v
            
            console.print("[green]✓ Extraction successful![/]")
            return True
        except Exception as e:
            console.print(f"[red]Failed to extract from resume: {e}[/]")
            return False


class SetupWizard:
    """Guided interactive setup for the entire system."""

    def __init__(self, profile: ApplicantProfile):
        self.profile = profile
        self.env_path = Path(".env")

    def run(self):
        """Run the full all-in-one setup wizard."""
        console.print(Panel.fit(
            "[bold cyan]Welcome to the Job Automation Setup Wizard[/]\n"
            "This wizard will help you configure your profile, API keys, and platform credentials.",
            title="Setup v2026"
        ))

        # Phase 7: Resume Import
        self._step_resume_import()

        self._step_personal_info()
        self._step_experience_summary()
        self._step_work_auth()
        self._step_llm_config()
        self._step_email_config()
        self._step_platform_config()
        self._step_search_config()

        # Final Review phase
        self._step_review_profile()

        self.profile.save()
        console.print("\n[bold green]✓ Setup complete! Your settings have been saved.[/]")
        console.print("[dim]Profile saved to data/profile.yaml[/]")
        console.print("[dim]Credentials saved to .env[/]")

    def _step_resume_import(self):
        console.print("\n[bold]Step 0: Resume Import (Optional)[/]")
        if Confirm.ask("Would you like to pre-fill your profile from a resume file?", default=True):
            path_str = Prompt.ask("Enter full path to resume (PDF or DOCX)")
            resume_path = Path(path_str.strip('"').strip("'"))
            if resume_path.exists():
                success = self.profile.import_from_resume(resume_path)
                if success:
                    # User Preferences from Phase 7 questions
                    self._update_env("BASE_RESUME_PDF" if resume_path.suffix.lower() == ".pdf" else "BASE_RESUME_DOCX", str(resume_path.absolute()))
                    console.print("[dim]Note: This resume also set as your base resume for applications.[/]")
            else:
                console.print("[yellow]Resume file not found. Continuing with manual setup...[/]")

    def _step_personal_info(self):
        console.print("\n[bold]1. Personal Information[/]")
        p = self.profile.data["personal"]
        p["first_name"] = Prompt.ask("First Name", default=p.get("first_name", ""))
        p["last_name"] = Prompt.ask("Last Name", default=p.get("last_name", ""))
        p["email"] = Prompt.ask("Email", default=p.get("email", config.YAHOO_EMAIL))
        p["phone"] = Prompt.ask("Phone", default=p.get("phone", ""))
        p["city"] = Prompt.ask("City", default=p.get("city", ""))
        p["linkedin_url"] = Prompt.ask("LinkedIn URL", default=p.get("linkedin_url", ""))
        p["github_url"] = Prompt.ask("Github URL", default=p.get("github_url", ""))
        p["portfolio_url"] = Prompt.ask("Portfolio/Website URL", default=p.get("portfolio_url", ""))

    def _step_experience_summary(self):
        console.print("\n[bold]1b. Professional Summary & Experience[/]")
        exp = self.profile.data["experience"]
        pref = self.profile.data["preferences"]
        
        exp["total_years"] = Prompt.ask("Total Years of Professional Experience", default=str(exp.get("total_years", "0.0")))
        exp["current_title"] = Prompt.ask("Current/Most Recent Job Title", default=exp.get("current_title", ""))
        
        console.print("\n[dim]AI Generated Summary (used for profile bios and applications):[/]")
        exp["summary"] = Prompt.ask("Global Professional Summary", default=exp.get("summary", ""))
        
        pref["notice_period"] = Prompt.ask("Notice Period (e.g. Immediately, 2 weeks)", default=pref.get("notice_period", "Immediately"))
        pref["remote_preference"] = Prompt.ask("Work Preference", choices=["Remote", "Hybrid", "Onsite"], default=pref.get("remote_preference", "Remote"))

    def _step_work_auth(self):
        console.print("\n[bold]2. Work Authorization & Preferences[/]")
        w = self.profile.data["work_authorization"]
        w["authorized_to_work"] = Confirm.ask("Are you authorized to work in your target country?", default=w.get("authorized_to_work", True))
        w["sponsorship_needed"] = Confirm.ask("Will you require visa sponsorship?", default=w.get("sponsorship_needed", False))
        
        pref = self.profile.data["preferences"]
        pref["willing_to_relocate"] = Confirm.ask("Are you willing to relocate?", default=pref.get("willing_to_relocate", True))
        pref["salary_expectation"] = Prompt.ask("Salary Expectation", default=pref.get("salary_expectation", "Open to discussion"))

    def _update_env(self, key: str, value: str):
        """Helper to update .env securely."""
        if not self.env_path.exists():
            self.env_path.touch()
        set_key(str(self.env_path), key, value)

    def _step_llm_config(self):
        console.print("\n[bold]3. LLM Configuration[/]")
        choices = ["openai", "gemini", "claude", "groq", "openrouter", "ollama", "lmstudio"]
        current = config.LLM_PROVIDER
        provider = Prompt.ask("Choose LLM Provider", choices=choices, default=current)
        self._update_env("LLM_PROVIDER", provider)

        if provider == "openai":
            key = Prompt.ask("OpenAI API Key", password=True, default=config.OPENAI_API_KEY)
            self._update_env("OPENAI_API_KEY", key)
        elif provider == "openrouter":
            key = Prompt.ask("OpenRouter API Key", password=True, default=os.getenv("OPENROUTER_API_KEY", ""))
            self._update_env("OPENROUTER_API_KEY", key)
            model = Prompt.ask("OpenRouter Model (e.g. google/gemini-2.0-flash-001)", default=config.OPENROUTER_MODEL)
            self._update_env("OPENROUTER_MODEL", model)
        elif provider == "gemini":
            key = Prompt.ask("Gemini API Key", password=True, default=os.getenv("GEMINI_API_KEY", ""))
            self._update_env("GEMINI_API_KEY", key)
        elif provider == "claude":
            key = Prompt.ask("Anthropic API Key", password=True, default=os.getenv("ANTHROPIC_API_KEY", ""))
            self._update_env("ANTHROPIC_API_KEY", key)
            model = Prompt.ask("Claude Model (e.g. claude-3-5-sonnet-20240620)", default=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620"))
            self._update_env("ANTHROPIC_MODEL", model)
        elif provider == "groq":
            key = Prompt.ask("Groq API Key", password=True, default=os.getenv("GROQ_API_KEY", ""))
            self._update_env("GROQ_API_KEY", key)
            model = Prompt.ask("Groq Model (e.g. llama-3.1-70b-versatile)", default=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"))
            self._update_env("GROQ_MODEL", model)
        elif provider == "ollama":
            url = Prompt.ask("Ollama URL", default=config.OLLAMA_BASE_URL)
            self._update_env("OLLAMA_BASE_URL", url)
            model = Prompt.ask("Ollama Model", default=config.OLLAMA_MODEL)
            self._update_env("OLLAMA_MODEL", model)
        elif provider == "lmstudio":
            url = Prompt.ask("LM Studio URL", default=config.LMSTUDIO_BASE_URL)
            self._update_env("LMSTUDIO_BASE_URL", url)
            model = Prompt.ask("LM Studio Model", default=config.LMSTUDIO_MODEL)
            self._update_env("LMSTUDIO_MODEL", model)

    def _step_email_config(self):
        console.print("\n[bold]4. Email Configuration (Scanner)[/]")
        email = Prompt.ask("Email (for scanning alerts)", default=config.YAHOO_EMAIL)
        self._update_env("YAHOO_EMAIL", email)
        password = Prompt.ask("App Password", password=True, default=config.YAHOO_APP_PASSWORD)
        self._update_env("YAHOO_APP_PASSWORD", password)

    def _step_platform_config(self):
        console.print("\n[bold]5. Platform Logins[/]")
        
        # LinkedIn
        li_email = Prompt.ask("LinkedIn Email", default=config.LINKEDIN_EMAIL or config.YAHOO_EMAIL)
        self._update_env("LINKEDIN_EMAIL", li_email)
        li_pass = Prompt.ask("LinkedIn Password", password=True, default=config.LINKEDIN_PASSWORD)
        self._update_env("LINKEDIN_PASSWORD", li_pass)
        
        # Indeed
        in_email = Prompt.ask("Indeed Email", default=config.INDEED_EMAIL or config.YAHOO_EMAIL)
        self._update_env("INDEED_EMAIL", in_email)
        in_pass = Prompt.ask("Indeed Password", password=True, default=config.INDEED_PASSWORD)
        self._update_env("INDEED_PASSWORD", in_pass)

        # Default password for account creation
        acc_pass = Prompt.ask(
            "Default Password for Account Creation (Workday, etc.)", 
            password=True, 
            default=os.getenv("ACCOUNT_PASSWORD", "JobBotPass!2024")
        )
        self._update_env("ACCOUNT_PASSWORD", acc_pass)

    def _step_search_config(self):
        console.print("\n[bold]6. Job Search Settings[/]")
        roles = Prompt.ask("Target Roles (comma-separated)", default=",".join(config.TARGET_ROLES))
        self._update_env("TARGET_ROLES", roles)
        score = IntPrompt.ask("Minimum Match Score (0-100)", default=config.MIN_ROLE_MATCH_SCORE)
        self._update_env("MIN_ROLE_MATCH_SCORE", str(score))

    def _step_review_profile(self):
        """Show a table of the profile and allow last minute edits."""
        while True:
            console.print("\n[bold]Step 7: Review & Finalize[/]")
            table = Table(title="Profile Data Summary", show_header=True, header_style="bold magenta")
            table.add_column("Section")
            table.add_column("Field")
            table.add_column("Value", style="dim")

            for section, fields in self.profile.data.items():
                if isinstance(fields, dict):
                    count = 0
                    for k, v in fields.items():
                        if k == "entries": continue
                        label = k.replace("_", " ").title()
                        table.add_row(section.title() if count == 0 else "", label, str(v))
                        count += 1
            
            console.print(table)
            
            if Confirm.ask("Does everything look correct?", default=True):
                break
            else:
                console.print("[yellow]Please review individual steps above to correct fields or manually edit data/profile.yaml after setup.[/]")
                if not Confirm.ask("Continue saving anyway?", default=False):
                    break
                break


def launch_wizard():
    """Entry point for the wizard."""
    profile = ApplicantProfile()
    wizard = SetupWizard(profile)
    wizard.run()

if __name__ == "__main__":
    launch_wizard()
