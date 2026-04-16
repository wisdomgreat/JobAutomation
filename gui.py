import os
import sys
import threading
import time
import subprocess
import webbrowser
from pathlib import Path
import customtkinter as ctk
import yaml
from dotenv import set_key
import re
import platform
import ctypes
from config import PROFILE_PATH, PROJECT_ROOT, _get, DATA_DIR, ENV_PATH, BASE_RESUME_PDF, BASE_RESUME_DOCX
from src.applicant_profile import ApplicantProfile
import json
from tkinter import filedialog
import shutil

def open_path(path):
    """Platform-agnostic file/folder opener."""
    path = str(path)
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin": # macOS
        subprocess.run(["open", path])
    else: # Linux
        subprocess.run(["xdg-open", path])

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Import existing backend modules
import config
from config import PROFILE_PATH, PROJECT_ROOT, _get
from src.tracker import Tracker
from src.applicant_bot import apply_to_job
from src.resume_builder import parse_resume
from datetime import datetime

# Configure CustomTkinter
ctk.set_appearance_mode("Dark") # Force Premium Dark Mode
ctk.set_default_color_theme("blue")

class LogRedirector:
    """Redirects stdout to the CustomTkinter Textbox."""
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, text):
        try:
            if not self.textbox.winfo_exists(): return
            clean_text = self._strip_ansi(text)
            self.textbox.insert(ctk.END, clean_text)
            self.textbox.see(ctk.END)
            self.textbox.update()
        except (Exception, RuntimeError):
            pass

        
    def _strip_ansi(self, text):
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)

    def flush(self):
        pass

class JobAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Sovereign Path Resolution
        self.db_path = config.DB_PATH
        self.tracker = Tracker(self.db_path)

        # Window Setup
        self.title(f"Sovereign Agent v{config.VERSION}")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # Set Icons
        try:
            icon_path = Path(resource_path("image/favicon.ico"))
            if icon_path.exists() and platform.system() == "Windows":
                self.iconbitmap(str(icon_path))
        except Exception as e:
            print(f"[UI] Warning: Could not set window icon: {e}")

        # Windows Taskbar Icon Fix
        if platform.system() == "Windows":
            try:
                myappid = 'SovereignAgent.V25.CareerAI'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception: pass

        self._old_stdout = sys.stdout
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Phase 33: TDWAS Onboarding Check
        self.after(500, self.check_onboarding)


        # Phase 32: Legal Compliance
        self.legal_var = ctk.BooleanVar(value=False)
        
        # Phase 27.2: AI Session Management
        self.key_visible = False
        self.provider_keys = {
            "openai": config.OPENAI_API_KEY,
            "gemini": config.GEMINI_API_KEY,
            "claude": config.ANTHROPIC_API_KEY,
            "groq": config.GROQ_API_KEY,
            "openrouter": config.OPENROUTER_API_KEY,
            "ollama": "", # Local
            "lmstudio": "" # Local
        }
        self.last_provider = config.LLM_PROVIDER
        
        # ─── Layout ───
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ─── Navigation Sidebar ───
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1) # Spacer

        # Sidebar Logo & Identity (High-DPI Support)
        try:
            from PIL import Image
            logo_img = Image.open(resource_path("image/logo.png"))
            self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(180, 180))
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, image=self.logo_image, text="")
        except Exception as e:
            print(f"[UI] Warning: Logo load failed: {e}")
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SOVEREIGN AGENT", font=ctk.CTkFont(size=22, weight="bold"))

        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10))

        # Nav Buttons (Sovereign Executive Style)
        self.dashboard_btn = self._create_nav_btn("🏠 DASHBOARD", 1, self.show_dashboard)
        self.search_btn = self._create_nav_btn("🔍 TARGET SCAN", 2, self.show_search)
        self.assets_btn = self._create_nav_btn("📋 ASSET HUB", 3, self.show_assets)
        self.crm_btn = self._create_nav_btn("🤝 CANDIDATE CRM", 4, self.show_crm)
        self.analytics_btn = self._create_nav_btn("📈 INTELLIGENCE", 5, self.show_analytics)
        self.settings_btn = self._create_nav_btn("⚙️ SYSTEM CORE", 6, self.show_settings)
        self.support_btn = self._create_nav_btn("🤝 HELP & SUPPORT", 7, self.show_support)

        # Live Status Card in Sidebar
        self.status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#121212", corner_radius=10, border_width=1, border_color="#333")
        self.status_frame.grid(row=11, column=0, padx=20, pady=20, sticky="ew")
        self.status_title = ctk.CTkLabel(self.status_frame, text="SYSTEM STATUS", font=ctk.CTkFont(size=10, weight="bold"))
        self.status_title.pack(pady=(10, 0))
        self.status_indic = ctk.CTkLabel(self.status_frame, text="● READY", text_color="#00d4ff", font=ctk.CTkFont(weight="bold"))
        self.status_indic.pack(pady=(0, 10))

        # ─── Main Content Area ───
        
        # 1. Dashboard Frame
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.dashboard_frame.grid_columnconfigure(0, weight=4) # Feed
        self.dashboard_frame.grid_columnconfigure(1, weight=3) # Terminal
        self.dashboard_frame.grid_rowconfigure(0, weight=1) # FIX: Allow expansion
        self._build_dashboard_ui()

        # SMART ONBOARDING: If no keys, show settings first
        if not _get("OPENROUTER_API_KEY") and not _get("OPENAI_API_KEY"):
            self.after(1000, lambda: self._show_onboarding_alert())
            self.after(1500, lambda: self.select_frame_by_name("Settings"))

        # ─── Framework Initialization ───
        
        # 2. Search Tab Frame
        self.search_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.search_frame.grid_columnconfigure(0, weight=1)
        self.search_frame.grid_rowconfigure(1, weight=1) 
        self._build_search_ui()

        # 3. Assets Frame (Resume Manager)
        self.assets_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.assets_frame.grid_columnconfigure(0, weight=1)
        self.assets_frame.grid_rowconfigure(2, weight=1)
        self._build_assets_ui()

        # 4. Analytics Frame
        self.analytics_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.analytics_frame.grid_columnconfigure(0, weight=1)
        self.analytics_frame.grid_rowconfigure(1, weight=1) 
        self._build_analytics_ui()

        # 4b. CRM Frame (NEW)
        self.crm_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.crm_frame.grid_columnconfigure(0, weight=1)
        self.crm_frame.grid_rowconfigure(2, weight=1)
        self._build_crm_ui()

        # 5. Settings Frame (Sovereign Command Center)
        self.settings_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame.grid_columnconfigure(0, weight=1)
        self._build_settings_ui()

        # 6. Support Frame
        self.support_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.support_frame.grid_columnconfigure(0, weight=1)
        self._build_support_ui()

        # Set Initial State
        self.select_frame_by_name("Dashboard")
        self.refresh_stats()

        # PHASE 24.5: Instant Console Redirection
        self.after(500, self.enable_redirection)

    def enable_redirection(self):
        """Safely take over stdout once the GUI is stable."""
        try:
            if hasattr(self, 'log_box') and self.log_box.winfo_exists():
                sys.stdout = LogRedirector(self.log_box)
                print("[System] Console handover complete. Logic stream active.")
        except Exception as e:
            print(f"[UI] Redirection failed: {e}")

    def on_closing(self):
        """Restore stdout and safe shutdown."""
        print("[System] Shifting to standby. Security protocols active.")
        try:
            if hasattr(self, '_old_stdout'):
                sys.stdout = self._old_stdout
        except Exception:
            pass
        self.destroy()
        sys.exit(0)

    def _show_onboarding_alert(self):
        print("\n" + "═"*50)
        print(" 🚀 WELCOME TO SOVEREIGN AGENT")
        print("" + "═"*50)
        print(" [SYSTEM] First-run detected. Please configure your")
        print(" [SYSTEM] API Keys in the 'SYSTEM CORE' tab to begin.")
        print("═"*50 + "\n")

    def _create_nav_btn(self, text, row, command):
        btn = ctk.CTkButton(self.sidebar_frame, text=text, fg_color="transparent", text_color=("gray90", "gray90"), 
                             hover_color="#34495e", anchor="w", font=ctk.CTkFont(size=14), height=45, command=command)
        btn.grid(row=row, column=0, padx=15, pady=5, sticky="ew")
        return btn

    def _build_dashboard_ui(self):
        # LEFT: Feed & Stats
        left_panel = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(20, 10), pady=20)
        left_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(left_panel, text="Control Center", font=ctk.CTkFont(size=28, weight="bold")).grid(row=0, column=0, sticky="w", pady=(0, 20))
        
        # Stats Row
        stats_row = ctk.CTkFrame(left_panel, fg_color="transparent")
        stats_row.grid(row=1, column=0, sticky="ew", pady=10)
        stats_row.grid_columnconfigure((0, 1, 2), weight=1)
        self.stat_apps = self._create_stat_card(stats_row, "SUCCESSFUL APPS", "0", 0)
        self.stat_recent = self._create_stat_card(stats_row, "LAST 24 HOURS", "0", 1)
        self.stat_rate = self._create_stat_card(stats_row, "WINS (MATCH RATE)", "0%", 2)

        # Scan Lookback Duration (Phase 27.0)
        lookback_frame = ctk.CTkFrame(left_panel, fg_color="#080808", corner_radius=10, border_width=1, border_color="#333")
        lookback_frame.grid(row=2, column=0, sticky="ew", pady=(20, 10))
        self.lookback_label = ctk.CTkLabel(lookback_frame, text="Scan Lookback: 3.0 days", font=ctk.CTkFont(size=11, weight="bold"))
        self.lookback_label.pack(side="left", padx=20, pady=15)
        self.lookback_slider = ctk.CTkSlider(lookback_frame, from_=0.1, to=30, number_of_steps=299, command=self.update_lookback_label)
        self.lookback_slider.set(3.0)
        self.lookback_slider.pack(side="left", expand=True, fill="x", padx=(0, 20))

        # Buttons
        self.run_btn = ctk.CTkButton(left_panel, text="⚡ LAUNCH AUTO-PIPELINE", fg_color="#00d4ff", hover_color="#00a8cc", text_color="black", height=60, font=ctk.CTkFont(size=16, weight="bold"), command=self.run_pipeline)
        self.run_btn.grid(row=3, column=0, sticky="ew", pady=10)
        self.run_btn.configure(state="disabled") # Locked until legal check

        # Job Feed
        self.feed_frame = ctk.CTkScrollableFrame(left_panel, label_text="RECENT MISSIONS", label_font=ctk.CTkFont(weight="bold"), height=400)
        self.feed_frame.grid(row=4, column=0, sticky="nsew", pady=10)
        left_panel.grid_rowconfigure(4, weight=1)

        # RIGHT: Live Terminal
        right_panel = ctk.CTkFrame(self.dashboard_frame, fg_color="#080808", corner_radius=15, border_width=1, border_color="#333")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=40)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_panel, text="LIVE OPERATIONS CONSOLE", font=ctk.CTkFont(size=12, weight="bold", family="Consolas"), text_color="#00d4ff").grid(row=0, column=0, pady=10)
        self.log_box = ctk.CTkTextbox(right_panel, fg_color="transparent", font=ctk.CTkFont(family="Consolas", size=11), text_color="#00d4ff", wrap="word")
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        # sys.stdout = LogRedirector(self.log_box) # MOVED to delayed enable_redirection

    def _build_assets_ui(self):
        ctk.CTkLabel(self.assets_frame, text="Asset Hub & Identity", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        
        # 1. Identity Status
        id_frame = ctk.CTkFrame(self.assets_frame, corner_radius=15, border_width=1, border_color="#333")
        id_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(id_frame, text="👤 AGENT IDENTITY (BRAIN)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00d4ff").pack(pady=10)
        
        # Check if profile is set
        profile = ApplicantProfile()
        name = profile.data.get('personal', {}).get('first_name', '') + " " + profile.data.get('personal', {}).get('last_name', '')
        if not name.strip(): name = "NOT CONFIGURED"
        
        ctk.CTkLabel(id_frame, text=f"Active Profile: {name}", text_color="gray").pack()
        
        btn_grid = ctk.CTkFrame(id_frame, fg_color="transparent")
        btn_grid.pack(pady=20, padx=20)
        ctk.CTkButton(btn_grid, text="📝 EDIT FULL IDENTITY", command=self.open_profile_editor).pack(side="left", padx=10)
        
        # 2. Resume Management
        res_frame = ctk.CTkFrame(self.assets_frame, corner_radius=15)
        res_frame.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(res_frame, text="📄 RESUME MANAGER", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=10)
        
        # Status indicators
        pdf_status = "✅ BASE_RESUME.PDF (Active)" if BASE_RESUME_PDF.exists() else "❌ PDF NOT FOUND"
        docx_status = "✅ BASE_RESUME.DOCX" if BASE_RESUME_DOCX.exists() else "❌ DOCX NOT FOUND"
        ctk.CTkLabel(res_frame, text=f"{pdf_status}\n{docx_status}", text_color="gray", font=ctk.CTkFont(size=11)).pack()
        
        up_grid = ctk.CTkFrame(res_frame, fg_color="transparent")
        up_grid.pack(pady=15)
        ctk.CTkButton(up_grid, text="📤 UPLOAD PDF", fg_color="#34495e", command=lambda: self.upload_asset("pdf")).pack(side="left", padx=5)
        ctk.CTkButton(up_grid, text="📤 UPLOAD DOCX", fg_color="#34495e", command=lambda: self.upload_asset("docx")).pack(side="left", padx=5)

    def upload_asset(self, ext):
        file = filedialog.askopenfilename(title=f"Select Resume ({ext.upper()})", filetypes=[(f"{ext.upper()} files", f"*.{ext}")])
        if file:
            try:
                target = BASE_RESUME_PDF if ext == "pdf" else BASE_RESUME_DOCX
                shutil.copy2(file, target)
                print(f"[Assets] Updated {ext.upper()} resume successfully in permanent storage.")
                self.after(500, self._build_assets_ui) # Refresh
                self.after(500, self.check_onboarding) # Re-check lock
            except Exception as e:
                print(f"[Assets] Upload failed: {e}")

    def open_profile_editor(self):
        ProfileEditorWindow(self)

    def refresh_assets_list(self):
        """Scan output folder for existing resumes."""
        for widget in self.asset_scroll.winfo_children(): widget.destroy()
        
        output_path = Path(config.OUTPUT_DIR)
        if not output_path.exists(): 
            ctk.CTkLabel(self.asset_scroll, text="No campaigns initiated yet.").pack(pady=20)
            return

        # Get subdirectories (dated)
        campaigns = sorted([d for d in output_path.iterdir() if d.is_dir()], reverse=True)
        for campaign in campaigns:
            for sub in sorted([s for s in campaign.iterdir() if s.is_dir()], reverse=True):
                row = ctk.CTkFrame(self.asset_scroll, fg_color="transparent")
                row.pack(fill="x", padx=10, pady=5)
                
                label_text = f"📂 {campaign.name} | {sub.name[:30]}..."
                ctk.CTkLabel(row, text=label_text, font=ctk.CTkFont(size=12)).pack(side="left", padx=10)
                
                ctk.CTkButton(row, text="OPEN FOLDER", width=120, height=28, fg_color="#34495e", 
                              command=lambda p=sub: open_path(p)).pack(side="right", padx=5)
                
                pdfs = list(sub.glob("*.pdf"))
                if pdfs:
                    ctk.CTkButton(row, text="VIEW PDF", width=100, height=28, fg_color="#00d4ff", hover_color="#00a8cc", text_color="black",
                                  command=lambda p=pdfs[0]: open_path(p)).pack(side="right", padx=5)

    def _build_analytics_ui(self):
        ctk.CTkLabel(self.analytics_frame, text="Intelligence Dashboard", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        self.chart_frame = ctk.CTkFrame(self.analytics_frame, corner_radius=15, fg_color="#1a1a1a")
        self.chart_frame.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        self.analytics_frame.grid_rowconfigure(1, weight=1)
        self.chart_canvas = ctk.CTkCanvas(self.chart_frame, background="#1a1a1a", highlightthickness=0)
        self.chart_canvas.pack(fill="both", expand=True, padx=30, pady=30)
 
    def _create_stat_card(self, parent, title, value, col):
        frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=12)
        frame.grid(row=0, column=col, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(frame, text=title, text_color="gray60", font=ctk.CTkFont(size=10, weight="bold")).pack(pady=(15, 0))
        val_label = ctk.CTkLabel(frame, text=value, font=ctk.CTkFont(size=28, weight="bold"))
        val_label.pack(pady=(0, 15))
        return val_label

    def _build_search_ui(self):
        ctk.CTkLabel(self.search_frame, text="Target Scan (Semi-Auto)", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        form = ctk.CTkFrame(self.search_frame, corner_radius=15)
        form.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        self.search_keywords = self._create_form_row(form, "Target Roles", "e.g. Cloud Architect, DevOps", 0)
        self.search_location = self._create_form_row(form, "Target Location", "e.g. London, Remote", 1)
        
        ctk.CTkLabel(form, text="Platform Hub", width=150, anchor="w").grid(row=2, column=0, padx=20, pady=20)
        self.search_platform = ctk.CTkOptionMenu(form, values=["LinkedIn", "Indeed", "Both"], width=300)
        self.search_platform.grid(row=2, column=1, padx=20, pady=20, sticky="w")

        self.search_btn_main = ctk.CTkButton(self.search_frame, text="🛰️ INITIATE SCAN", height=60, font=ctk.CTkFont(weight="bold"), fg_color="#00d4ff", hover_color="#00a8cc", text_color="black", command=self.run_semi_auto_search)
        self.search_btn_main.grid(row=3, column=0, padx=30, pady=10, sticky="ew")
        self.search_btn_main.configure(state="disabled") # Locked until legal check

        # Phase 27.0: Tactical Controls
        tactical_frame = ctk.CTkFrame(self.search_frame, fg_color="#080808", corner_radius=15, border_width=1, border_color="#333")
        tactical_frame.grid(row=4, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(tactical_frame, text="TACTICAL CONTROLS", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack(pady=(10, 5))
        
        # Match Score Slider
        slider_frame = ctk.CTkFrame(tactical_frame, fg_color="transparent")
        slider_frame.pack(fill="x", padx=20, pady=5)
        self.match_label = ctk.CTkLabel(slider_frame, text=f"Match Intensity: {config.MATCH_SCORE_THRESHOLD}%", width=150, anchor="w")
        self.match_label.pack(side="left")
        self.match_slider = ctk.CTkSlider(slider_frame, from_=0, to=100, number_of_steps=20, command=self.update_match_label)
        self.match_slider.set(config.MATCH_SCORE_THRESHOLD)
        self.match_slider.pack(side="left", expand=True, fill="x", padx=10)

        # Search Intensity Slider (Phase 27.0)
        intensity_frame = ctk.CTkFrame(tactical_frame, fg_color="transparent")
        intensity_frame.pack(fill="x", padx=20, pady=5)
        self.intensity_label = ctk.CTkLabel(intensity_frame, text="Search Intensity: 5 jobs", width=150, anchor="w")
        self.intensity_label.pack(side="left")
        self.intensity_slider = ctk.CTkSlider(intensity_frame, from_=1, to=50, number_of_steps=49, command=self.update_intensity_label)
        self.intensity_slider.set(5)
        self.intensity_slider.pack(side="left", expand=True, fill="x", padx=10)
        
        # Stealth Toggle
        self.stealth_var = ctk.BooleanVar(value=True)
        self.stealth_toggle = ctk.CTkSwitch(tactical_frame, text="BEHAVIORAL STEALTH (Human Mimicry)", variable=self.stealth_var, fg_color="#00d4ff")
        self.stealth_toggle.pack(pady=10)

    def update_match_label(self, val):
        config.MATCH_SCORE_THRESHOLD = int(val)
        self.match_label.configure(text=f"Match Intensity: {int(val)}%")

    def update_intensity_label(self, val):
        self.intensity_label.configure(text=f"Search Intensity: {int(val)} jobs")

    def update_lookback_label(self, val):
        self.lookback_label.configure(text=f"Scan Lookback: {float(val):.1f} days")

    def _create_form_row(self, parent, label, dummy, row):
        ctk.CTkLabel(parent, text=label, width=150, anchor="w").grid(row=row, column=0, padx=20, pady=15)
        entry = ctk.CTkEntry(parent, placeholder_text=dummy, height=40)
        entry.grid(row=row, column=1, padx=20, pady=15, sticky="ew")
        return entry

    def _build_settings_ui(self):
        ctk.CTkLabel(self.settings_frame, text="Core Configuration", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        
        # 1. AI Intelligence Hub (Dynamic)
        ai_frame = ctk.CTkFrame(self.settings_frame, corner_radius=15, border_width=1, border_color="#333")
        ai_frame.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        
        ctk.CTkLabel(ai_frame, text="🧠 AI INTELLIGENCE HUB", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00d4ff").pack(pady=10)
        
        # Phase 27.2: Status Ribbon
        self.ai_status_ribbon = ctk.CTkLabel(ai_frame, text="", font=ctk.CTkFont(size=10), text_color="gray")
        self.ai_status_ribbon.pack(pady=(0, 10))
        self._update_ai_status_ribbon()
        
        # Provider Dropdown
        prov_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
        prov_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(prov_frame, text="Active Intelligence", width=150, anchor="w").pack(side="left")
        self.provider_dropdown = ctk.CTkOptionMenu(prov_frame, values=["openai", "gemini", "claude", "groq", "openrouter", "ollama", "lmstudio"], 
                                                   command=self.on_provider_change)
        self.provider_dropdown.set(config.LLM_PROVIDER)
        self.provider_dropdown.pack(side="right", expand=True, fill="x", padx=10)

        # Model Dropdown (ComboBox for custom entry)
        model_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
        model_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(model_frame, text="Model Identifier", width=150, anchor="w").pack(side="left")
        
        self.model_combo = ctk.CTkComboBox(model_frame, values=[], variable=ctk.StringVar(value=self._get_current_model()))
        self.model_combo.pack(side="right", expand=True, fill="x", padx=10)
        self._update_model_list(config.LLM_PROVIDER)
        
        # API Key Field (Shared Entry with Visibility Toggle)
        self.api_key_frame = ctk.CTkFrame(ai_frame, fg_color="transparent")
        self.api_key_frame.pack(fill="x", padx=20, pady=15)
        self.api_key_label = ctk.CTkLabel(self.api_key_frame, text="API Access Key", width=150, anchor="w")
        self.api_key_label.pack(side="left")
        
        entry_container = ctk.CTkFrame(self.api_key_frame, fg_color="transparent")
        entry_container.pack(side="right", expand=True, fill="x", padx=10)
        
        self.api_key_entry = ctk.CTkEntry(entry_container, show="*")
        self.api_key_entry.pack(side="left", expand=True, fill="x")
        self.api_key_entry.bind("<KeyRelease>", self.update_api_key_buffer)
        
        self.eye_btn = ctk.CTkButton(entry_container, text="👁️", width=35, height=35, fg_color="transparent", 
                                     hover_color="#333", command=self.toggle_api_visibility)
        self.eye_btn.pack(side="right", padx=(5, 0))
        
        # Populate current
        self.api_key_entry.insert(0, str(self.provider_keys.get(config.LLM_PROVIDER, "")))

        # 2. Sovereign Explorer (Directory Access)
        expl_frame = ctk.CTkFrame(self.settings_frame, corner_radius=15)
        expl_frame.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        ctk.CTkLabel(expl_frame, text="📂 SOVEREIGN EXPLORER", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=20, pady=20)
        path_text = f"Storage: .../{DATA_DIR.name}"
        ctk.CTkLabel(expl_frame, text=path_text, text_color="gray").pack(side="left", padx=10)
        ctk.CTkButton(expl_frame, text="OPEN DATA FOLDER", width=150, fg_color="#34495e", command=lambda: open_path(DATA_DIR)).pack(side="right", padx=(10, 20), pady=20)
        ctk.CTkButton(expl_frame, text="🧹 PURGE STALE ASSETS", width=150, fg_color="#e74c3c", hover_color="#c0392b", command=self.run_purge).pack(side="right", padx=10, pady=20)

        # 3. Target Identity & Global Logins
        ctk.CTkLabel(self.settings_frame, text="Global Platform Credentials", font=ctk.CTkFont(size=14, weight="bold")).grid(row=10, column=0, padx=30, pady=(30, 10), sticky="w")
        
        self.env_entries = {}
        # We define all necessary credentials here
        credential_keys = [
            ("LINKEDIN_EMAIL", "LinkedIn Username"),
            ("LINKEDIN_PASSWORD", "LinkedIn Password"),
            ("INDEED_EMAIL", "Indeed Username"),
            ("INDEED_PASSWORD", "Indeed Password"),
            ("YAHOO_EMAIL", "Yahoo/Search Email"),
            ("YAHOO_APP_PASSWORD", "Yahoo App Password")
        ]
        
        for i, (key, label) in enumerate(credential_keys):
            frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
            frame.grid(row=i+15, column=0, padx=30, pady=5, sticky="ew")
            ctk.CTkLabel(frame, text=label, width=200, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400, show="*" if "PASSWORD" in key else "")
            entry.insert(0, str(_get(key)))
            entry.pack(side="right", expand=True, fill="x", padx=10)
            self.env_entries[key] = entry
        
        # Legal Compliance (Phase 32)
        legal_frame = ctk.CTkFrame(self.settings_frame, fg_color="#2c3e50", corner_radius=10)
        legal_frame.grid(row=90, column=0, padx=30, pady=20, sticky="ew")
        
        ctk.CTkLabel(legal_frame, text="⚠️ LEGAL ACKNOWLEDGEMENT", font=ctk.CTkFont(weight="bold", size=12)).pack(pady=(10, 5))
        ctk.CTkLabel(legal_frame, text="This tool is for educational purposes. I accept full responsibility for all activities\nand acknowledge the risk of account suspension on third-party platforms.", font=ctk.CTkFont(size=11), text_color="gray90").pack(pady=5)
        
        self.legal_check = ctk.CTkCheckBox(legal_frame, text="I AGREE TO THE TERMS & DISCLAIMER", variable=self.legal_var, command=self.toggle_legal_lock, fg_color="#e74c3c")
        self.legal_check.pack(pady=10)

        self.save_btn = ctk.CTkButton(self.settings_frame, text="💾 SAVE SYSTEM CORE", height=50, command=self.save_settings)
        self.save_btn.grid(row=100, column=0, padx=30, pady=20, sticky="e")

    def toggle_legal_lock(self):
        state = "normal" if self.legal_var.get() else "disabled"
        self.run_btn.configure(state=state)
        self.search_btn_main.configure(state=state)
        if self.legal_var.get():
            print("[Legal] Terms accepted. Operation clearance granted.")
        else:
            print("[Legal] Terms withdrawn. Hardware locked.")

    def _build_support_ui(self):
        ctk.CTkLabel(self.support_frame, text="Community & Support Hub", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        
        # Security Card
        sec_card = ctk.CTkFrame(self.support_frame, fg_color="#1a1a1a", border_width=1, border_color="#333", corner_radius=15)
        sec_card.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        ctk.CTkLabel(sec_card, text="🛡️ SECURITY & PRIVACY VERIFIED", font=ctk.CTkFont(weight="bold", size=12), text_color="#00d4ff").pack(pady=(15, 5))
        ctk.CTkLabel(sec_card, text="Sovereign Agent is 100% Local. No passwords or personal data ever leave your machine.\nWe do not use telemetry, tracking, or external cloud storage for your secrets.", font=ctk.CTkFont(size=11), text_color="gray").pack(pady=(0, 15))

        # Support Grid
        grid = ctk.CTkFrame(self.support_frame, fg_color="transparent")
        grid.grid(row=2, column=0, padx=30, pady=10, sticky="ew")
        grid.grid_columnconfigure((0, 1), weight=1)

        # Feature Requests
        feat_box = ctk.CTkFrame(grid, corner_radius=15)
        feat_box.grid(row=0, column=0, padx=(0, 10), pady=10, sticky="nsew")
        ctk.CTkLabel(feat_box, text="💡 Have an idea?", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        ctk.CTkLabel(feat_box, text="Suggest a new tool or feature\nto the community board.", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=5)
        ctk.CTkButton(feat_box, text="REQUEST FEATURE", command=lambda: webbrowser.open(f"https://github.com/{config.GITHUB_REPO}/issues/new?labels=enhancement")).pack(pady=20, padx=20)

        # Bug Reports
        bug_box = ctk.CTkFrame(grid, corner_radius=15)
        bug_box.grid(row=0, column=1, padx=(10, 0), pady=10, sticky="nsew")
        ctk.CTkLabel(bug_box, text="🐞 Found a bug?", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        ctk.CTkLabel(bug_box, text="Help us improve. Report technical\nissues or errors here.", text_color="gray", font=ctk.CTkFont(size=11)).pack(pady=5)
        ctk.CTkButton(bug_box, text="REPORT ISSUE", fg_color="#e74c3c", hover_color="#c0392b", command=lambda: webbrowser.open(f"https://github.com/{config.GITHUB_REPO}/issues/new?labels=bug")).pack(pady=20, padx=20)

        # Documentation
        doc_box = ctk.CTkFrame(self.support_frame, corner_radius=15)
        doc_box.grid(row=3, column=0, padx=30, pady=10, sticky="ew")
        ctk.CTkLabel(doc_box, text="📖 Documentation & Guide", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=20, pady=20)
        ctk.CTkButton(doc_box, text="OPEN WIKI", width=150, command=lambda: webbrowser.open(f"https://github.com/{config.GITHUB_REPO}/wiki")).pack(side="right", padx=20, pady=20)
        
        # TDWAS Branding Footer
        ctk.CTkLabel(self.support_frame, text="© 2026 TDWAS Technology | Sovereign Agent Project", text_color="gray40", font=ctk.CTkFont(size=10)).grid(row=4, column=0, pady=20)

    def _get_current_model(self):
        p = config.LLM_PROVIDER
        if p == "openai": return config.OPENAI_MODEL
        if p == "gemini": return config.GEMINI_MODEL
        if p == "claude": return config.ANTHROPIC_MODEL
        if p == "groq": return config.GROQ_MODEL
        if p == "ollama": return config.OLLAMA_MODEL
        if p == "openrouter": return config.OPENROUTER_MODEL
        return "default"

    def _update_model_list(self, provider):
        models = {
            "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-preview"],
            "gemini": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
            "claude": ["claude-3-5-sonnet-latest", "claude-3-5-haiku-latest", "claude-3-opus-20240229"],
            "groq": ["llama-3.3-70b-versatile", "mixtral-8x7b-32768", "llama-3.1-8b-instant"],
            "ollama": ["llama3", "mistral", "phi3", "nomic-embed-text"],
            "openrouter": ["google/gemini-2.0-flash-001", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-chat"],
            "lmstudio": ["local-model"]
        }
        self.model_combo.configure(values=models.get(provider, []))
        self.model_combo.set(self._get_current_model())

    def _update_ai_status_ribbon(self):
        """Show which providers are currently configured with keys."""
        ready = []
        for prov, key in self.provider_keys.items():
            if prov not in ["ollama", "lmstudio"] and key and len(key) > 5:
                ready.append(prov.upper())
        
        if ready:
            self.ai_status_ribbon.configure(text=f"CONFIGURED: {' | '.join(ready)}", text_color="#2ecc71")
        else:
            self.ai_status_ribbon.configure(text="NO KEYS CONFIGURED (LOCAL ONLY)", text_color="gray")

    def toggle_api_visibility(self):
        """Toggle mask on API key field."""
        self.key_visible = not self.key_visible
        self.api_key_entry.configure(show="" if self.key_visible else "*")
        self.eye_btn.configure(text="🔒" if self.key_visible else "👁️")

    def update_api_key_buffer(self, event=None):
        """Sync current entry to buffer in real-time."""
        prov = self.provider_dropdown.get()
        if prov not in ["ollama", "lmstudio"]:
            self.provider_keys[prov] = self.api_key_entry.get()
            self._update_ai_status_ribbon()

    def on_provider_change(self, provider):
        """Phase 27.2: Hybrid Key Management & Persistence."""
        # 1. Save current key to buffer for the OLD provider first
        current_key = self.api_key_entry.get()
        if self.last_provider not in ["ollama", "lmstudio"]:
            self.provider_keys[self.last_provider] = current_key

        print(f"[UI] Switching intelligence provider to: {provider}")
        self._update_model_list(provider)
        
        # 2. Update Entry State & Value
        if provider in ["ollama", "lmstudio"]:
            self.api_key_entry.delete(0, "end")
            self.api_key_entry.configure(placeholder_text="Not required for local AI", state="disabled")
        else:
            self.api_key_entry.configure(state="normal")
            self.api_key_entry.delete(0, "end")
            stored_key = self.provider_keys.get(provider, "")
            self.api_key_entry.insert(0, str(stored_key))
            
            placeholders = {
                "openai": "sk-...",
                "gemini": "AIza...",
                "openrouter": "sk-or-v1-...",
                "claude": "sk-ant-...",
                "groq": "gsk_..."
            }
            self.api_key_entry.configure(placeholder_text=placeholders.get(provider, "Enter Key"))
        
        self.last_provider = provider

    def check_onboarding(self):
        """Detect first-run state & LOCK UX if not ready."""
        flag_file = DATA_DIR / ".onboarding_done"
        profile_ready = ApplicantProfile().data.get('personal', {}).get('first_name', '') != ''
        resume_ready = BASE_RESUME_PDF.exists() or BASE_RESUME_DOCX.exists()
        
        if not flag_file.exists() or not profile_ready or not resume_ready:
            print("[System] SECURITY LOCK: Mandatory Mission Briefing Required.")
            # Lock UI
            for btn in [self.dashboard_btn, self.search_btn, self.analytics_btn]:
                btn.configure(state="disabled")
            self.run_btn.configure(state="disabled")
            
            # Auto-switch to Support or just show wizard
            self.select_frame_by_name("Support")
            OnboardingWizard(self)
        else:
            # Unlock
            for btn in [self.dashboard_btn, self.search_btn, self.analytics_btn]:
                btn.configure(state="normal")
            self.show_dashboard()

    def select_frame_by_name(self, name):
        # Update Nav Styles
        nav_map = {
            "Dashboard": self.dashboard_btn, "Search": self.search_btn, 
            "Assets": self.assets_btn, "CRM": self.crm_btn,
            "Analytics": self.analytics_btn, "Settings": self.settings_btn, 
            "Support": self.support_btn
        }
        for n, b in nav_map.items():
            b.configure(fg_color="#34495e" if n == name else "transparent", border_width=1 if n == name else 0)

        # Swap Frames
        frame_map = {
            "Dashboard": self.dashboard_frame, "Search": self.search_frame, 
            "Assets": self.assets_frame, "CRM": self.crm_frame,
            "Analytics": self.analytics_frame, "Settings": self.settings_frame, 
            "Support": self.support_frame
        }
        for n, f in frame_map.items():
            if n == name:
                f.grid(row=0, column=1, sticky="nsew")
                if n == "Dashboard": self.refresh_job_feed()
                if n == "Analytics": self._draw_analytics_chart()
                if n == "CRM": self.refresh_crm_feed()
            else: f.grid_forget()

    def show_dashboard(self): self.select_frame_by_name("Dashboard")
    def show_search(self): self.select_frame_by_name("Search")
    def show_assets(self): self.select_frame_by_name("Assets")
    def show_crm(self): self.select_frame_by_name("CRM")
    def show_analytics(self): self.select_frame_by_name("Analytics")
    def show_settings(self): self.select_frame_by_name("Settings")
    def show_support(self): self.select_frame_by_name("Support")

    def _build_crm_ui(self):
        """Elite Candidate CRM Interface (Phase 28.0)."""
        ctk.CTkLabel(self.crm_frame, text="Candidate Outreach & CRM", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        
        # Action Bar
        bar = ctk.CTkFrame(self.crm_frame, fg_color="transparent")
        bar.grid(row=1, column=0, padx=30, pady=(0, 20), sticky="ew")
        
        self.check_crm_btn = ctk.CTkButton(bar, text="🔍 SCAN RECRUITER INTELLIGENCE", fg_color="#00d4ff", hover_color="#00a8cc", text_color="black", font=ctk.CTkFont(weight="bold"), command=self.run_crm_scan)
        self.check_crm_btn.pack(side="left", padx=5)
        
        # Scrollable CRM Feed
        self.crm_scroll = ctk.CTkScrollableFrame(self.crm_frame, label_text="DETECTED RECRUITER SIGNALS", label_font=ctk.CTkFont(weight="bold"))
        self.crm_scroll.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        self.crm_frame.grid_rowconfigure(2, weight=1)

    def refresh_crm_feed(self):
        """Populate the CRM tab with outreach data."""
        for widget in self.crm_scroll.winfo_children(): widget.destroy()
        
        outreach = self.tracker.get_outreach()
        if not outreach:
            ctk.CTkLabel(self.crm_scroll, text="No recruiter signals detected yet.", text_color="gray").pack(pady=40)
            return
            
        for i, msg in enumerate(outreach):
            row = ctk.CTkFrame(self.crm_scroll, fg_color=("#121212" if i % 2 == 0 else "transparent"), corner_radius=10, border_width=1, border_color="#333")
            row.pack(fill="x", padx=10, pady=5)
            
            # Sentiment Badge
            s_color = "#2ecc71" if msg['sentiment'] == "positive" else "#f1c40f"
            s_label = ctk.CTkLabel(row, text="●", text_color=s_color, font=ctk.CTkFont(size=20))
            s_label.pack(side="left", padx=(15, 5))
            
            # Header Info
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            
            sender_id = msg['sender'].split("<")[0].strip() if "<" in msg['sender'] else msg['sender'][:25]
            ctk.CTkLabel(info, text=f"{sender_id} | {msg['date_received']}", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack(anchor="w")
            ctk.CTkLabel(info, text=msg['subject'], font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w")
            
            # Action Buttons
            ctk.CTkButton(row, text="VIEW THREAD", width=100, height=28, fg_color="#34495e", command=lambda m=msg: self.show_outreach_details(m)).pack(side="right", padx=15)

    def show_outreach_details(self, msg):
        """Show full email body in a popup."""
        popup = ctk.CTkToplevel(self)
        popup.title(f"Recruiter Pulse: {msg['subject']}")
        popup.geometry("600x500")
        
        text = ctk.CTkTextbox(popup, wrap="word", font=("Consolas", 11))
        text.pack(fill="both", expand=True, padx=20, pady=20)
        text.insert("0.0", f"FROM: {msg['sender']}\nSUBJECT: {msg['subject']}\nSENTIMENT: {msg['sentiment'].upper()}\n\n" + "═"*50 + "\n\n" + msg['body'])
        text.configure(state="disabled")

    def run_crm_scan(self):
        """Manually trigger the Recruiter Intelligence scanner."""
        self.check_crm_btn.configure(state="disabled", text="SCANNING...")
        def _run():
            from src.email_scanner import EmailScanner
            scanner = EmailScanner()
            new = scanner.check_for_outreach()
            print(f"[Intelligence] Scan complete. Found {new} new recruiter signals.")
            self.after(0, self.refresh_crm_feed)
            self.after(0, lambda: self.check_crm_btn.configure(state="normal", text="🔍 SCAN RECRUITER INTELLIGENCE"))
            
        threading.Thread(target=_run, daemon=True).start()

    def _draw_analytics_chart(self):
        """Draw real bar chart from mission data."""
        try:
            self.chart_canvas.delete("all")
            stats = self.tracker.get_analytics()
            total = stats.get("total", 0)
            if total == 0:
                self.chart_canvas.create_text(200, 100, text="NOT ENOUGH DATA YET", fill="gray")
                return

            w, h = self.chart_canvas.winfo_width(), self.chart_canvas.winfo_height()
            if w < 100: self.after(100, self._draw_analytics_chart); return
            
            # Using Status Breakdown for the chart
            status_data = stats.get("statuses", {})
            if not status_data: status_data = {"new": 1}

            data_keys = list(status_data.keys())
            data_vals = list(status_data.values())
            
            padding, chart_w, chart_h = 60, w - 120, h - 120
            bar_w = (chart_w / len(data_vals)) * 0.6
            max_val = max(data_vals)
            
            for i, val in enumerate(data_vals):
                x = padding + (i * (chart_w / len(data_vals))) + (chart_w/len(data_vals) - bar_w)/2
                bar_h = (val / max_val) * chart_h
                y = h - padding - bar_h
                
                # Color by status
                color = "#2ecc71" if data_keys[i] == "applied" else "#3498db" if data_keys[i] == "new" else "#e74c3c"
                self.chart_canvas.create_rectangle(x, y, x + bar_w, h - padding, fill=color, outline="")
                self.chart_canvas.create_text(x + bar_w/2, y - 15, text=f"{data_keys[i].upper()}\n({val})", fill="white", font=("Arial", 9, "bold"))
        except: pass

    def refresh_stats(self):
        stats = self.tracker.get_analytics()
        self.stat_apps.configure(text=str(stats.get("applied", 0)))
        self.stat_rate.configure(text=f"{stats.get('success_rate', 0)}%")
        self.stat_recent.configure(text=str(stats.get("recent_7_days", 0)))
        self.refresh_job_feed()

    def refresh_job_feed(self):
        for widget in self.feed_frame.winfo_children(): widget.destroy()
        apps = self.tracker.get_all()[:30]
        for i, app in enumerate(apps):
            row = ctk.CTkFrame(self.feed_frame, fg_color=("#1a1a1a" if i % 2 == 0 else "transparent"), corner_radius=8)
            row.pack(fill="x", padx=10, pady=3); row.grid_columnconfigure(0, weight=1)
            
            # 1. Source & Time Info (NEW)
            source_icon = "🔗" if "Indeed" in app.source else "💼"
            time_str = app.date_found.split(" ")[1][:5] if " " in app.date_found else ""
            date_str = "Today" if app.date_found.startswith(datetime.now().strftime("%Y-%m-%d")) else app.date_found.split(" ")[0][5:]
            meta_text = f"{source_icon} {date_str} {time_str}"
            
            meta_label = ctk.CTkLabel(row, text=meta_text, font=ctk.CTkFont(size=9), text_color="gray", width=80)
            meta_label.pack(side="left", padx=5)

            # 2. Match Score Badge
            score_color = "#00d4ff" if app.match_score >= 85 else "#f1c40f" if app.match_score >= 70 else "#e74c3c"
            score_label = ctk.CTkLabel(row, text=f"{app.match_score}%", text_color=score_color, font=ctk.CTkFont(size=11, weight="bold"), width=35)
            score_label.pack(side="left", padx=2)
            
            # 3. Job Info
            info_text = f"{app.company[:12]} | {app.job_title[:22]}..."
            ctk.CTkLabel(row, text=info_text, font=ctk.CTkFont(size=11), anchor="w").pack(side="left", padx=5, pady=10)
            
            # 4. Action Buttons
            if app.status == "new":
                ctk.CTkButton(row, text="APPLY NOW", width=80, height=26, fg_color="#00d4ff", hover_color="#00a8cc", text_color="black",
                               font=ctk.CTkFont(size=10, weight="bold"), command=lambda a=app: self.surgical_apply(a)).pack(side="right", padx=5)
            else:
                ctk.CTkLabel(row, text=app.status.upper(), font=ctk.CTkFont(size=10, weight="bold"), text_color="gray", width=80).pack(side="right", padx=5)
                
            ctk.CTkButton(row, text="VIEW", width=50, height=26, fg_color="#34495e", 
                           font=ctk.CTkFont(size=10), command=lambda u=app.apply_url: webbrowser.open(u)).pack(side="right", padx=5)

    def surgical_apply(self, app):
        """Phase 26.0 Surgical Apply from GUI."""
        self.status_indic.configure(text="● SURGICAL", text_color="#3498db")
        def _run():
            resume_text = ""
            try: resume_text = parse_resume()
            except: pass
            
            print(f"\n[GUI] Launching Surgical Apply for: {app.job_title}...")
            # We use global imports now to avoid re-importing issues
            result = apply_to_job(app.apply_url, app.resume_path, app.cover_letter_path, resume_text, app.source)
            if result["success"]:
                self.tracker.update_status(app.id, "applied", result["message"])
                print(f"✓ Application successful!")
            else:
                print(f"✗ Failed: {result['message']}")
            
            self.after(0, lambda: self.status_indic.configure(text="● READY", text_color="#2ecc71"))
            self.after(0, self.refresh_stats)
            
        threading.Thread(target=_run, daemon=True).start()

    def save_settings(self):
        # Update General / Logins
        for k, e in self.env_entries.items():
            if e.get(): set_key(str(ENV_PATH), k, e.get())
        
        # Phase 27.2: Global AI Persistence
        # First sync current open field to buffer
        self.update_api_key_buffer()
        
        # Save all buffered keys in one shot
        key_map = {
            "openai": "OPENAI_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "claude": "ANTHROPIC_API_KEY",
            "groq": "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY"
        }
        
        for prov, key_val in self.provider_keys.items():
            if prov in key_map and key_val:
                set_key(str(ENV_PATH), key_map[prov], key_val)
                setattr(config, key_map[prov], key_val)
        
        # Update Active Provider & Model
        active_prov = self.provider_dropdown.get()
        active_model = self.model_combo.get()
        set_key(str(ENV_PATH), "LLM_PROVIDER", active_prov)
        config.LLM_PROVIDER = active_prov
        
        model_env_map = {
            "openai": "OPENAI_MODEL", "gemini": "GEMINI_MODEL",
            "claude": "ANTHROPIC_MODEL", "groq": "GROQ_MODEL",
            "ollama": "OLLAMA_MODEL", "openrouter": "OPENROUTER_MODEL"
        }
        if active_prov in model_env_map:
            set_key(str(ENV_PATH), model_env_map[active_prov], active_model)
            setattr(config, model_env_map[active_prov], active_model)

        # Update Local AI URLs
        if active_prov == "ollama":
            set_key(str(ENV_PATH), "OLLAMA_BASE_URL", config.OLLAMA_BASE_URL)
        
        print("[Core] TDWAS System intelligence synchronized to persistent storage.")

    def run_purge(self):
        """Invoke surgical maintenance from GUI."""
        from src.maintenance import purge_old_outputs
        try:
            print("[System] Initiating document purge (Last 14 days safe)...")
            deleted, space = purge_old_outputs(14)
            print(f"✓ Success! Removed {deleted} folders, freeing {space} MB.")
        except Exception as e:
            print(f"✗ Purge failed: {e}")

    def run_pipeline(self):
        self.status_indic.configure(text="● ACTIVE", text_color="#f1c40f")
        lookback = self.lookback_slider.get()
        def _run():
            from main import run_auto_pipeline
            try: 
                run_auto_pipeline(days_back=lookback)
            finally: 
                # Phase 24.1: Thread-safe UI updates
                self.after(0, lambda: self.status_indic.configure(text="● READY", text_color="#2ecc71"))
                self.after(0, self.refresh_stats)
        threading.Thread(target=_run, daemon=True).start()

    def run_semi_auto_search(self):
        kw, loc_str, plat = self.search_keywords.get(), self.search_location.get(), self.search_platform.get().lower()
        if not kw or not loc_str: return
        
        # Support multiple locations (Phase 27.0)
        locations = [l.strip() for l in loc_str.split(",") if l.strip()]
        if not locations: locations = [loc_str]
        
        limit_val = int(self.intensity_slider.get())
        
        def _run():
            from main import run_search_pipeline
            try: 
                run_search_pipeline(plat, kw, locations, limit=limit_val)
            finally:
                # Phase 24.1: Thread-safe UI updates
                self.after(0, self.refresh_stats)
        threading.Thread(target=_run, daemon=True).start()


    def send_feedback(self):
        msg = self.feedback_text.get("0.0", "end").strip()
        if not msg: return
        from src.feedback import send_discord_feedback
        if send_discord_feedback(msg): self.feedback_text.delete("0.0", "end")


class OnboardingWizard(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("TDWAS Sovereign Mission Briefing")
        self.geometry("700x600")
        self.transient(parent)
        self.grab_set()
        self.parent = parent
        self.step = 1
        
        # UI Setup
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        self.head = ctk.CTkLabel(self, text="MISSION BRIEFING", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00d4ff")
        self.head.pack(pady=30)
        
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=40)
        
        self.btn_next = ctk.CTkButton(self, text="NEXT STEP →", height=50, command=self.next_step)
        self.btn_next.pack(side="bottom", pady=(20, 40))
        
        self.err_label = ctk.CTkLabel(self, text="", text_color="#e74c3c", font=ctk.CTkFont(size=12, weight="bold"))
        self.err_label.pack(side="bottom")
        
        self.show_step_1()

    def show_step_1(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        self.err_label.configure(text="")
        ctk.CTkLabel(self.content_frame, text="STEP 1: IDENTITY CORE", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        self.e_name = ctk.CTkEntry(self.content_frame, placeholder_text="First Name *", width=300)
        self.e_name.pack(pady=5)
        self.e_last = ctk.CTkEntry(self.content_frame, placeholder_text="Last Name", width=300)
        self.e_last.pack(pady=5)

    def show_step_2(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        self.err_label.configure(text="")
        ctk.CTkLabel(self.content_frame, text="STEP 2: AGENT ASSETS", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        ctk.CTkLabel(self.content_frame, text="Upload your master resume (PDF or DOCX)", text_color="gray").pack()
        ctk.CTkButton(self.content_frame, text="📂 SELECT RESUME FILE", fg_color="#34495e", command=self.wizard_upload).pack(pady=20)
        self.upload_status = ctk.CTkLabel(self.content_frame, text="Status: Waiting...", text_color="yellow")
        self.upload_status.pack()

    def wizard_upload(self):
        file = filedialog.askopenfilename(title="Select Resume", filetypes=[("Resume", "*.pdf;*.docx")])
        if file:
            ext = file.split('.')[-1]
            target = BASE_RESUME_PDF if ext == "pdf" else BASE_RESUME_DOCX
            shutil.copy2(file, target)
            self.upload_status.configure(text="✅ Resume Linked!", text_color="green")

    def show_step_3(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        self.err_label.configure(text="")
        ctk.CTkLabel(self.content_frame, text="STEP 3: INTELLIGENCE Hub", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        self.w_prov = ctk.CTkOptionMenu(self.content_frame, values=["openai", "gemini", "openrouter", "ollama"], width=300)
        self.w_prov.pack(pady=10)
        self.w_key = ctk.CTkEntry(self.content_frame, placeholder_text="API Key (Leave blank if Local)", show="*", width=300)
        self.w_key.pack(pady=5)

    def next_step(self):
        self.err_label.configure(text="")
        if self.step == 1:
            if not self.e_name.get():
                self.err_label.configure(text="⚠️ FIRST NAME IS MANDATORY")
                return
            try:
                p = ApplicantProfile()
                p.data['personal']['first_name'] = self.e_name.get()
                p.data['personal']['last_name'] = self.e_last.get()
                p.save()
                self.step = 2
                self.show_step_2()
            except Exception as e:
                self.err_label.configure(text=f"❌ FAILED TO SAVE: {str(e)[:40]}")
        elif self.step == 2:
            if not (BASE_RESUME_PDF.exists() or BASE_RESUME_DOCX.exists()):
                self.err_label.configure(text="⚠️ RESUME FILE REQUIRED FOR MISSION")
                return
            self.step = 3
            self.show_step_3()
        elif self.step == 3:
            set_key(str(ENV_PATH), "LLM_PROVIDER", self.w_prov.get())
            if self.w_key.get():
                k_map = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
                if self.w_prov.get() in k_map: set_key(str(ENV_PATH), k_map[self.w_prov.get()], self.w_key.get())
            
            self.step = 4
            self.show_step_4()
        elif self.step == 4:
            try:
                p = ApplicantProfile()
                p.data['personal']['city'] = self.e_city.get()
                p.data['personal']['province'] = self.e_prov.get()
                p.data['experience']['summary'] = self.e_bio.get("0.0", "end").strip()
                p.save()
                
                (DATA_DIR / ".onboarding_done").touch()
                self.parent.check_onboarding() # Refresh lock
                self.destroy()
            except Exception as e:
                self.err_label.configure(text=f"❌ FAILED TO FINALIZE: {str(e)[:40]}")

    def show_step_4(self):
        for w in self.content_frame.winfo_children(): w.destroy()
        ctk.CTkLabel(self.content_frame, text="STEP 4: MISSION BIO & INTEL", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        
        self.e_city = ctk.CTkEntry(self.content_frame, placeholder_text="Current City (e.g. Toronto)", width=300)
        self.e_city.pack(pady=5)
        self.e_prov = ctk.CTkEntry(self.content_frame, placeholder_text="State/Province (e.g. ON)", width=300)
        self.e_prov.pack(pady=5)
        
        ctk.CTkLabel(self.content_frame, text="Professional Bio / Summary", font=ctk.CTkFont(size=11)).pack(pady=(10, 0))
        self.e_bio = ctk.CTkTextbox(self.content_frame, height=150, width=400)
        self.e_bio.pack(pady=10)
        
        # Pre-fill if resume extraction worked
        p = ApplicantProfile()
        self.e_city.insert(0, p.data['personal'].get('city', ''))
        self.e_prov.insert(0, p.data['personal'].get('province', ''))
        self.e_bio.insert("0.0", p.data['experience'].get('summary', ''))

class ProfileEditorWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Identity Sovereign Editor")
        self.geometry("800x700")
        self.profile = ApplicantProfile()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.tabview.add("Personal")
        self.tabview.add("Experience")
        self.tabview.add("Skills")
        
        # (Simplified for now, will expand to all 90+ fields in full build)
        p = self.profile.data['personal']
        self.e_first = self._add_field(self.tabview.tab("Personal"), "First Name", p.get('first_name'), 0)
        self.e_last = self._add_field(self.tabview.tab("Personal"), "Last Name", p.get('last_name'), 1)
        self.e_email = self._add_field(self.tabview.tab("Personal"), "Contact Email", p.get('email'), 2)
        
        exp = self.profile.data['experience']
        self.e_title = self._add_field(self.tabview.tab("Experience"), "Current Title", exp.get('current_title'), 0)
        
        ctk.CTkButton(self, text="💾 SAVE TO IDENTITY", command=self.save).grid(row=1, column=0, pady=20)

    def _add_field(self, parent, label, val, row):
        ctk.CTkLabel(parent, text=label).grid(row=row, column=0, padx=10, pady=5)
        e = ctk.CTkEntry(parent, width=300)
        e.insert(0, str(val))
        e.grid(row=row, column=1, padx=10, pady=5)
        return e

    def save(self):
        self.profile.data['personal']['first_name'] = self.e_first.get()
        self.profile.data['personal']['last_name'] = self.e_last.get()
        self.profile.data['personal']['email'] = self.e_email.get()
        self.profile.data['experience']['current_title'] = self.e_title.get()
        self.profile.save()
        print("[System] Identity updated successfully.")
        self.destroy()

if __name__ == "__main__":
    JobAutomationApp().mainloop()

