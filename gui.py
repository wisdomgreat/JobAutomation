import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import sys
import os
import threading
import time
import shutil
import platform
import ctypes
import webbrowser
import math
import random
from pathlib import Path
from datetime import datetime
from dotenv import set_key

# Internal Core Imports
from src.tracker import Tracker
from src.applicant_profile import ApplicantProfile
import config
from config import ENV_PATH, DATA_DIR, BASE_RESUME_PDF, BASE_RESUME_DOCX

# Theme Initialization
ctk.set_appearance_mode(config.GUI_APPEARANCE_MODE)
ctk.set_default_color_theme(config.GUI_ACCENT_COLOR)

def resource_path(relative_path):
    """Sovereign Asset Resolver: Supports Dev and PyInstaller environments."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def open_path(path):
    """Platform-agnostic directory explorer."""
    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        import subprocess
        subprocess.Popen(["open", str(path)])
    else:
        import subprocess
        subprocess.Popen(["xdg-open", str(path)])

def _get(key, default=""):
    """Legacy helper for ENV migration."""
    return os.getenv(key, default)

class LogRedirector:
    """Redirects stdout to a CTkTextbox for mission telemetry."""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        if string.strip():
            # Colorize output based on content
            color = "gray"
            if "✓" in string or "Success" in string: color = "#2ecc71"
            elif "✗" in string or "Error" in string or "Failed" in string: color = "#e74c3c"
            elif "[System]" in string or "TELEMETRY" in string: color = "#00d4ff"
            elif "..." in string: color = "gray60"
            
            self.text_widget.after(0, lambda: self._safe_append(string, color))

    def flush(self):
        pass

    def _safe_append(self, string, color):
        try:
            self.text_widget.configure(state="normal")
            # Create a tag for the color if it doesn't exist
            tag_name = f"color_{color.replace('#','')}"
            self.text_widget.tag_config(tag_name, foreground=color)
            
            self.text_widget.insert("end", string + "\n", tag_name)
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        except Exception:
            pass

# ─── Main Application Engine ───

class JobAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Sovereign Path Resolution
        self.db_path = config.DB_PATH
        self.tracker = Tracker(self.db_path)
        self.profile = ApplicantProfile() # Phase 36.3: Centralized Profile Instance
        
        # Ensure Critical Folders Exist
        (DATA_DIR / "output").mkdir(parents=True, exist_ok=True)
        (DATA_DIR / "logs").mkdir(parents=True, exist_ok=True)
        
        # Phase 31.0: Guided Mode State
        self.guided_var = tk.BooleanVar(value=True) # Default to Guided

        # Window Setup
        self.title(f"Sovereign Agent v{config.VERSION}")
        self.geometry("1400x900")
        self.minsize(1100, 800)
        
        # Set Icons
        try:
            icon_path = Path(resource_path("image/favicon.ico"))
            if icon_path.exists() and platform.system() == "Windows":
                self.iconbitmap(str(icon_path))
        except Exception: pass

        # Windows Taskbar Icon Fix
        if platform.system() == "Windows":
            try:
                myappid = 'SovereignAgent.V25.CareerAI'
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            except Exception: pass

        self._old_stdout = sys.stdout
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # UI State & AI Configuration
        self._current_frame_name = "Dashboard"
        self._initializing = True # Flag to block UI events during startup
        self.key_visible = False
        self.legal_var = ctk.BooleanVar(value=True)
        self.active_tasks = []
        
        self.provider_keys = {
            "openai": config.OPENAI_API_KEY,
            "gemini": config.GEMINI_API_KEY,
            "claude": config.ANTHROPIC_API_KEY,
            "groq": config.GROQ_API_KEY,
            "ollama": config.OLLAMA_BASE_URL,
            "lmstudio": config.LMSTUDIO_BASE_URL,
            "openrouter": config.OPENROUTER_API_KEY
        }
        
        self.provider_models = {
            "openai": ["gpt-4o", "gpt-4o-mini", "o1-preview"],
            "claude": ["claude-3-5-sonnet-latest", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
            "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash-exp"],
            "groq": ["llama-3.3-70b-versatile", "llama3-70b-8192", "mixtral-8x7b-32768"],
            "ollama": ["llama3", "mistral", "phi3", "custom..."],
            "lmstudio": ["local-model"],
            "openrouter": ["google/gemini-2.0-flash-001", "anthropic/claude-3.5-sonnet", "deepseek/deepseek-chat"]
        }
        
        # ─── Layout ───
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ─── Navigation Sidebar ───
        self.sidebar_frame = ctk.CTkFrame(self, width=280, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1) # Spacer

        # Sidebar Logo (Modern & Clean)
        try:
            from PIL import Image
            logo_img = Image.open(resource_path("image/logo.png"))
            self.logo_image = ctk.CTkImage(light_image=logo_img, dark_image=logo_img, size=(200, 200))
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, image=self.logo_image, text="")
        except Exception:
            self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="🛡️ SOVEREIGN\nAGENT", font=ctk.CTkFont(size=24, weight="bold"))

        self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 30))

        # Nav Buttons
        self.nav_btns = {}
        self.dash_btn = self._create_nav_btn("📊 DASHBOARD", 1, "Dashboard")
        self.scan_btn = self._create_nav_btn("🔍 TARGET SCAN", 2, "Scan")
        self.asset_btn = self._create_nav_btn("📂 ASSET HUB", 3, "Assets")
        self.crm_btn = self._create_nav_btn("🤝 CANDIDATE CRM", 4, "CRM")
        self.intel_btn = self._create_nav_btn("🧠 INTELLIGENCE", 5, "Intel")
        self.core_btn = self._create_nav_btn("⚙️ SYSTEM CORE", 6, "Core")
        self.help_btn = self._create_nav_btn("❓ HELP & SUPPORT", 7, "Support")
        self.analytics_btn = self._create_nav_btn("📊 ANALYTICS HUB", 8, "Analytics")

        # System Health Card
        self.health_card = ctk.CTkFrame(self.sidebar_frame, fg_color="#121212", corner_radius=12, border_width=1, border_color="#333")
        self.health_card.grid(row=11, column=0, padx=20, pady=30, sticky="ew")
        
        status_inner = ctk.CTkFrame(self.health_card, fg_color="transparent")
        status_inner.pack(pady=15, padx=15, fill="x")
        
        ctk.CTkLabel(status_inner, text="SYSTEM STATUS", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack(anchor="w")
        self.status_indic = ctk.CTkLabel(status_inner, text="● READY", text_color="#2ecc71", font=ctk.CTkFont(size=14, weight="bold"))
        self.status_indic.pack(anchor="w", pady=(2, 0))
        
        self.battery_lvl = ctk.CTkProgressBar(status_inner, height=4, progress_color="#00d4ff")
        self.battery_lvl.pack(fill="x", pady=(10, 0))
        self.battery_lvl.set(1.0)

        # ─── Main Content Hubs ───
        
        # 1. Dashboard (Metrics & Telemetry)
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.dashboard_frame.grid_columnconfigure(0, weight=1)
        self.dashboard_frame.grid_rowconfigure(2, weight=2) # charts
        self.dashboard_frame.grid_rowconfigure(3, weight=1) # telemetry
        self._build_dashboard_ui()
        # 8. Analytics (Frontier v34)
        self.analytics_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.analytics_frame.grid_columnconfigure(0, weight=1)
        self._build_analytics_ui()

        # 2. Target Scan (Intelligence & Search)
        self.scan_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.scan_frame.grid_columnconfigure(0, weight=1)
        self._build_scan_ui()

        # 3. Asset Hub (Document Explorer)
        self.asset_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.asset_frame.grid_columnconfigure(0, weight=1)
        self._build_asset_hub_ui()

        # 4. Candidate CRM (Application Tracker)
        self.crm_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.crm_frame.grid_columnconfigure(0, weight=1)
        self.crm_frame.grid_rowconfigure(2, weight=1)
        self._build_crm_ui()

        # 5. Intelligence (AI Synapse Core)
        self.intel_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.intel_frame.grid_columnconfigure(0, weight=1)
        self._build_intelligence_ui()

        # 6. System Core (Profile & Identity)
        self.core_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.core_frame.grid_columnconfigure(0, weight=1)
        self._build_system_core_ui()

        # 7. Help & Support
        self.help_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.help_frame.grid_columnconfigure(0, weight=1)
        self._build_help_ui()

        # Default to Dashboard
        self.select_frame_by_name("Dashboard")
        
        # Power-on Sequence
        self.after(500, self.enable_redirection)
        self.after(1000, self.check_onboarding)
        self.after(2000, self.refresh_stats_loop)
        self.after(3000, self.background_update_check)
        self._initializing = False

    def background_update_check(self):
        """Threaded non-blocking check for new mission directives."""
        def run_check():
            try:
                from src.update_manager import check_for_updates, get_update_info
                if check_for_updates():
                    info = get_update_info()
                    self.after(0, lambda: self._signal_update_available(info))
            except: pass
        threading.Thread(target=run_check, daemon=True).start()

    def _signal_update_available(self, info=None):
        """Visual notification with one-click seamless update."""
        version_text = f"v{info['version']}" if info and info.get('version') else "NEW"
        
        if hasattr(self, 'update_notif_label'):
            self.update_notif_label.configure(
                text=f"⚡ UPDATE {version_text} AVAILABLE — CLICK TO INSTALL", 
                text_color="#2ecc71", 
                cursor="hand2"
            )
            self.update_notif_label.bind("<Button-1>", lambda e: self._seamless_update())
            print(f"[System] ⚡ Alert: Sovereign Agent {version_text} is available. Click the banner to install seamlessly.")

    def _run_in_thread(self, func, *args, name="Task", **kwargs):
        """Standard engine for executing mission-critical background tasks."""
        def wrapper():
            try:
                self.status_indic.configure(text=f"● {name.upper()} ACTIVE", text_color="#00d4ff")
                self.battery_lvl.configure(progress_color="#00d4ff")
                func(*args, **kwargs)
                print(f"[System] {name} mission complete.")
                self.status_indic.configure(text="● READY", text_color="#2ecc71")
                self.battery_lvl.configure(progress_color="#00d4ff")
            except Exception as e:
                print(f"[Error] {name} failure: {e}")
                self.status_indic.configure(text="● CRITICAL ERROR", text_color="#e74c3c")
                self.battery_lvl.configure(progress_color="#e74c3c")

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        self.active_tasks.append(thread)
        return thread

    # ─── Navigation Sidebar Logic ───
    def _create_nav_btn(self, text, row, name):
        btn = ctk.CTkButton(self.sidebar_frame, text=text, height=55, corner_radius=0, border_spacing=12,
                           fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
                           anchor="w", font=ctk.CTkFont(size=13, weight="bold"), command=lambda: self.on_nav_click(name))
        btn.grid(row=row, column=0, sticky="ew")
        self.nav_btns[name] = btn
        return btn

    def on_nav_click(self, name):
        """Strategic Hub Switching with auto-refresh intelligence."""
        if name == "Analytics": self.refresh_analytics()
        if name == "CRM": self.refresh_crm_feed()
        if name == "Dashboard": self.refresh_stats()
        self.select_frame_by_name(name)

    def select_frame_by_name(self, name):
        """High-performance hub switching with visual feedback."""
        frames = {
            "Dashboard": self.dashboard_frame, 
            "Scan": self.scan_frame, 
            "Assets": self.asset_frame,
            "CRM": self.crm_frame,
            "Intel": self.intel_frame,
            "Core": self.core_frame,
            "Support": self.help_frame,
            "Analytics": self.analytics_frame
        }
        for n, frame in frames.items():
            if n == name:
                self._current_frame_name = name
                frame.grid(row=0, column=1, sticky="nsew")
                self.nav_btns[n].configure(fg_color=("gray75", "gray25"), text_color="#00d4ff")
            else:
                frame.grid_forget()
                self.nav_btns[n].configure(fg_color="transparent", text_color=("gray10", "gray90"))

    def _build_analytics_ui(self):
        """Sector 8: Advanced Mission Intelligence (Frontier v34)."""
        header = ctk.CTkLabel(self.analytics_frame, text="Mission Analytics & Strategic ROI", font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")

        # ROI Grid
        roi_card = self._create_card(self.analytics_frame, "📊 PLATFORM EFFICIENCY (ROI)")
        roi_card.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        
        self.roi_scroll = ctk.CTkScrollableFrame(roi_card, height=300, fg_color="transparent")
        self.roi_scroll.grid(row=1, column=0, padx=15, pady=20, sticky="ew")

    def refresh_analytics(self):
        """Update the Analytics Hub with fresh mission data."""
        try:
            stats = self.tracker.get_stats()
            # Clear ROI scroll
            for child in self.roi_scroll.winfo_children(): child.destroy()
            
            roi = stats.get('platform_roi', {})
            for plat, data in roi.items():
                row = ctk.CTkFrame(self.roi_scroll, fg_color="#1a1a1a", corner_radius=8)
                row.pack(fill="x", pady=2, padx=5)
                ctk.CTkLabel(row, text=plat.upper(), width=120, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=15)
                
                # Progress Bar for Applied vs Discovered
                bar = ctk.CTkProgressBar(row, width=200, height=8, progress_color="#2980b9")
                bar.pack(side="left", padx=20)
                rate = data['applied'] / (data['total'] if data['total'] > 0 else 1)
                bar.set(rate)
                
                ctk.CTkLabel(row, text=f"{data['applied']} Applied / {data['total']} Hits", text_color="gray").pack(side="left", padx=15)
                
                if data['interviews'] > 0:
                    ctk.CTkLabel(row, text=f"🎯 {data['interviews']} INTERVIEWS", text_color="#2ecc71", font=ctk.CTkFont(weight="bold")).pack(side="right", padx=15)
        except Exception as e:
            print(f"[Error] Failed to refresh analytics: {e}")

    # ─── Sector Builders ───────────────────────────────────────────────
    
    def _build_dashboard_ui(self):
        """Sector 1: Mission Command & High-Speed Telemetry."""
        lbl = ctk.CTkLabel(self.dashboard_frame, text="Mission Command Dashboard", font=ctk.CTkFont(size=28, weight="bold"))
        lbl.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")

        # Stats Cards Grid
        stats_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        stats_frame.grid(row=1, column=0, padx=40, pady=(0, 25), sticky="ew")
        stats_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.stat_apps = self._create_stat_card(stats_frame, "📊 DEPLOYED APPS", "0", 0)
        self.stat_interviews = self._create_stat_card(stats_frame, "🎤 INTERVIEW LEADS", "0", 1)
        self.stat_discoveries = self._create_stat_card(stats_frame, "🔍 INTEL TARGETS", "0", 2)
        self.stat_success = self._create_stat_card(stats_frame, "⚡ EFFICIENCY RATE", "0%", 3)
        
        # Phase 32.7: Update Notification Label
        self.update_notif_label = ctk.CTkLabel(self.dashboard_frame, text="", font=ctk.CTkFont(size=12, weight="bold"))
        self.update_notif_label.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="e")

        # Mission Intelligence Visuals (New Phase 32.0)
        visuals_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        visuals_frame.grid(row=2, column=0, padx=40, pady=(5, 10), sticky="nsew")
        visuals_frame.grid_columnconfigure((0, 1), weight=1)

        # Funnel Chart (Mission Progress)
        self.funnel_card = self._create_card(visuals_frame, "📊 MISSION PROGRESS FUNNEL")
        self.funnel_card.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        self.funnel_canvas = ctk.CTkCanvas(self.funnel_card, height=240, bg="#0d1117", highlightthickness=0)
        self.funnel_canvas.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="nsew")

        # Pie Chart (Platform Coverage)
        self.pie_card = self._create_card(visuals_frame, "🎯 PLATFORM DENSITY")
        self.pie_card.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        self.pie_canvas = ctk.CTkCanvas(self.pie_card, height=240, bg="#0d1117", highlightthickness=0)
        self.pie_canvas.grid(row=1, column=0, padx=20, pady=(5, 20), sticky="nsew")

        # Main Deck (Terminal & Quick Actions)
        main_deck = ctk.CTkFrame(self.dashboard_frame, corner_radius=15, border_width=1, border_color="#333")
        main_deck.grid(row=3, column=0, padx=40, pady=(5, 30), sticky="nsew")
        main_deck.grid_columnconfigure(0, weight=1)
        main_deck.grid_rowconfigure(0, weight=1)

        # Terminal
        term_frame = ctk.CTkFrame(main_deck, fg_color="transparent")
        term_frame.grid(row=0, column=0, padx=25, pady=25, sticky="nsew")
        
        ctk.CTkLabel(term_frame, text="📡 REAL-TIME MISSION TELEMETRY", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00d4ff").pack(anchor="w", pady=(0, 10))
        self.log_box = ctk.CTkTextbox(term_frame, font=("Fira Code", 13), fg_color="#0a0a0a", text_color="#2ecc71")
        self.log_box.pack(fill="both", expand=True)

        # Quick Control Panel
        ctrl_panel = ctk.CTkFrame(main_deck, width=280, fg_color="#121212", corner_radius=10)
        ctrl_panel.grid(row=0, column=1, padx=25, pady=25, sticky="ns")
        
        ctk.CTkLabel(ctrl_panel, text="QUICK MISSION CONTROLS", font=ctk.CTkFont(size=11, weight="bold")).pack(pady=(30, 20))
        
        # Phase 36.0: Readiness Checklist Widget
        readiness_frame = ctk.CTkFrame(ctrl_panel, fg_color="transparent")
        readiness_frame.pack(pady=(0, 20), padx=20, fill="x")
        
        ctk.CTkLabel(readiness_frame, text="MISSION READINESS", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack(anchor="w", padx=10)
        
        self.ready_ai = ctk.CTkLabel(readiness_frame, text="○ AI Synapse", font=ctk.CTkFont(size=12))
        self.ready_ai.pack(anchor="w", padx=10, pady=2)
        
        self.ready_id = ctk.CTkLabel(readiness_frame, text="○ Identity Sync", font=ctk.CTkFont(size=12))
        self.ready_id.pack(anchor="w", padx=10, pady=2)
        
        self.ready_resume = ctk.CTkLabel(readiness_frame, text="○ Master Resume", font=ctk.CTkFont(size=12))
        self.ready_resume.pack(anchor="w", padx=10, pady=2)
        
        ctk.CTkButton(ctrl_panel, text="🚀 FULL AUTO-PILOT", height=50, fg_color="#27ae60", hover_color="#2ecc71", font=ctk.CTkFont(weight="bold"), 
                     command=self.run_full_pipeline).pack(pady=10, padx=30, fill="x")
        
        ctk.CTkButton(ctrl_panel, text="🧪 TEST AI SYNAPSE", height=45, fg_color="#34495e", command=self.test_ai_synapse).pack(pady=10, padx=30, fill="x")
        
        self.stop_btn = ctk.CTkButton(ctrl_panel, text="🛑 EMERGENCY ABORT", height=45, fg_color="#e74c3c", hover_color="#c0392b", command=self.stop_pipeline)
        self.stop_btn.pack(pady=(20, 0), padx=30, fill="x")

    def _build_scan_ui(self):
        """Sector 2: Tactical Intelligence & Search Matrix."""
        header = ctk.CTkLabel(self.scan_frame, text="Target Scan & Intelligence", font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")

        # 1. Email Intelligence Card
        email_card = self._create_card(self.scan_frame, "📩 RECRUITER SIGNAL DETECTION")
        email_card.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        
        ctk.CTkLabel(email_card, text="Scan your inbox for interview requests and recruiter messages.", text_color="gray").grid(row=1, column=0, padx=25, pady=(10, 0), sticky="w")
        
        # Phase 32.3: Email Scan Platform Filter
        self.email_btn = ctk.CTkButton(email_card, text="🔍 INITIATE EMAIL SCAN", height=45, fg_color="#2980b9", command=self.run_email_scan)
        self.email_btn.grid(row=2, column=0, padx=25, pady=20, sticky="w")

        # 2. Search Matrix Card
        search_card = self._create_card(self.scan_frame, "🛰️ GLOBAL SEARCH MATRIX")
        search_card.grid(row=2, column=0, padx=40, pady=10, sticky="ew")
        
        ctk.CTkLabel(search_card, text="Trigger tactical search campaigns across multiple job boards.", text_color="gray").grid(row=1, column=0, padx=25, pady=(10, 0), sticky="w")
        ctk.CTkButton(search_card, text="🧭 LAUNCH SEARCH MATRIX", height=45, fg_color="#8e44ad", command=self.show_search_form).grid(row=2, column=0, padx=25, pady=20, sticky="w")

        # 3. Precision Striking
        prec_card = self._create_card(self.scan_frame, "🎯 SURGICAL URL STRIKE")
        prec_card.grid(row=3, column=0, padx=40, pady=10, sticky="ew")
        
        self.surgical_url_entry = ctk.CTkEntry(prec_card, placeholder_text="Paste job URL here...", height=45)
        self.surgical_url_entry.grid(row=1, column=0, padx=25, pady=(20, 10), sticky="ew")
        
        # Phase 32.3: Surgical Platform Override
        self.strike_plat_var = ctk.StringVar(value="Auto-Detect")
        self.strike_plat_menu = ctk.CTkOptionMenu(prec_card, variable=self.strike_plat_var, 
                                               values=["Auto-Detect", "LinkedIn", "Indeed", "ZipRecruiter", "Dice", "Wellfound", "BuiltIn"],
                                               width=140, height=45, fg_color="#34495e")
        self.strike_plat_menu.grid(row=1, column=1, padx=10, pady=(20, 10))
        
        ctk.CTkButton(prec_card, text="🚀 EXECUTE STRIKE", height=45, font=ctk.CTkFont(weight="bold"), 
                     command=self.run_surgical_apply).grid(row=1, column=2, padx=(0, 25), pady=(20, 10))
        
        # Guided Mode Toggle
        ctk.CTkCheckBox(prec_card, text="Enable Hand-in-Hand Guided Mode (Recommended)", 
                        variable=self.guided_var, font=ctk.CTkFont(size=12)).grid(row=2, column=0, padx=25, pady=(0, 20), sticky="w")

        # 4. Tactical Controls Card
        tac_card = self._create_card(self.scan_frame, "🎛️ TACTICAL CONTROLS")
        tac_card.grid(row=4, column=0, padx=40, pady=10, sticky="ew")

        tac_inner = ctk.CTkFrame(tac_card, fg_color="transparent")
        tac_inner.grid(row=1, column=0, padx=25, pady=(10, 25), sticky="ew")
        tac_inner.grid_columnconfigure(1, weight=1)

        # Match Intensity Slider
        self.match_label = ctk.CTkLabel(tac_inner, text=f"Match Intensity: {config.MATCH_SCORE_THRESHOLD}%", 
                                        font=ctk.CTkFont(size=13), text_color="gray90")
        self.match_label.grid(row=0, column=0, padx=(0, 20), pady=8, sticky="w")
        
        self.match_slider = ctk.CTkSlider(tac_inner, from_=30, to=100, number_of_steps=70,
                                           progress_color="#00d4ff", button_color="#00d4ff", button_hover_color="#00b8e6",
                                           command=self._on_match_slider)
        self.match_slider.set(config.MATCH_SCORE_THRESHOLD)
        self.match_slider.grid(row=0, column=1, padx=0, pady=8, sticky="ew")
        
        # Search Intensity Slider
        self.search_label = ctk.CTkLabel(tac_inner, text=f"Search Intensity: {config.MAX_JOBS_PER_SCAN} jobs", 
                                          font=ctk.CTkFont(size=13), text_color="gray90")
        self.search_label.grid(row=1, column=0, padx=(0, 20), pady=8, sticky="w")
        
        self.search_slider = ctk.CTkSlider(tac_inner, from_=1, to=50, number_of_steps=49,
                                            progress_color="#00d4ff", button_color="#00d4ff", button_hover_color="#00b8e6",
                                            command=self._on_search_slider)
        self.search_slider.set(config.MAX_JOBS_PER_SCAN)
        self.search_slider.grid(row=1, column=1, padx=0, pady=8, sticky="ew")
        
        # Behavioral Stealth Toggle
        self.stealth_var = ctk.BooleanVar(value=config.STEALTH_MODE)
        stealth_row = ctk.CTkFrame(tac_inner, fg_color="transparent")
        stealth_row.grid(row=2, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        
        self.stealth_switch = ctk.CTkSwitch(stealth_row, text="BEHAVIORAL STEALTH (Human Mimicry)", 
                                             variable=self.stealth_var, progress_color="#00d4ff",
                                             font=ctk.CTkFont(size=13, weight="bold"),
                                             command=self._on_stealth_toggle)
        self.stealth_switch.pack(anchor="center")

    def _build_asset_hub_ui(self):
        """Sector 3: Asset Explorer (Resumes & Documents)."""
        header = ctk.CTkLabel(self.asset_frame, text="Mission Asset Hub", font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")
        
        # Folder Card
        dir_card = self._create_card(self.asset_frame, "📂 GENERATED MISSION ASSETS")
        dir_card.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        
        ctk.CTkLabel(dir_card, text="View and manage tailored resumes and cover letters.", text_color="gray").grid(row=1, column=0, padx=25, pady=(10, 0), sticky="w")
        
        btn_row = ctk.CTkFrame(dir_card, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=25, pady=25, sticky="w")
        
        ctk.CTkButton(btn_row, text="📂 OPEN OUTPUT FOLDER", command=lambda: open_path(config.OUTPUT_DIR)).pack(side="left", padx=(0, 15))
        ctk.CTkButton(btn_row, text="📑 GENERATE NEW KIT", fg_color="#34495e", command=lambda: self.run_surgical_apply(only_docs=True)).pack(side="left")

        # Master Asset Commander (v30.2.10)
        master_card = self._create_card(self.asset_frame, "🛡️ MASTER ASSET CONTROL")
        master_card.grid(row=2, column=0, padx=40, pady=10, sticky="ew")
        
        ctk.CTkLabel(master_card, text="Upload your base resume to enable autonomous tailoring.", text_color="gray").grid(row=1, column=0, padx=25, pady=(10, 0), sticky="w")
        
        m_btn_row = ctk.CTkFrame(master_card, fg_color="transparent")
        m_btn_row.grid(row=2, column=0, padx=25, pady=25, sticky="w")
        
        ctk.CTkButton(m_btn_row, text="📤 UPLOAD MASTER RESUME", fg_color="#2980b9", hover_color="#3498db", command=self.upload_master_resume).pack(side="left")

        # Phase 30.5: Stealth & Browser Monitoring
        mon_card = self._create_card(self.asset_frame, "🖥️ MISSION MONITORING")
        mon_card.grid(row=3, column=0, padx=40, pady=10, sticky="ew")
        
        mon_inner = ctk.CTkFrame(mon_card, fg_color="transparent")
        mon_inner.grid(row=1, column=0, padx=25, pady=20, sticky="ew")
        
        self.watch_bot_var = ctk.BooleanVar(value=not config.HEADLESS_BROWSER)
        self.watch_bot_check = ctk.CTkCheckBox(mon_inner, text="WATCH THE BOT WORK (Show Browser Window)", variable=self.watch_bot_var, command=self.save_mission_strategy)
        self.watch_bot_check.grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(mon_inner, text="Disable this to run in silent stealth mode.", text_color="gray", font=ctk.CTkFont(size=10)).grid(row=1, column=0, padx=28, sticky="w")

    def _build_crm_ui(self):
        """Sector 4: Candidate CRM & Application Tracker."""
        header = ctk.CTkLabel(self.crm_frame, text="Candidate Outreach CRM", font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")

        # Active Feed (Table)
        self.feed_frame = ctk.CTkFrame(self.crm_frame, corner_radius=15, border_width=1, border_color="#333")
        self.feed_frame.grid(row=1, column=0, padx=40, pady=(0, 30), sticky="nsew")
        self.feed_frame.grid_columnconfigure(0, weight=1)
        self.feed_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.feed_frame, text="🤝 MISSION TRACKER (tracker.db)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00d4ff").grid(row=0, column=0, padx=25, pady=(20, 10), sticky="w")
        
        self.feed_scroll = ctk.CTkScrollableFrame(self.feed_frame, fg_color="transparent")
        self.feed_scroll.grid(row=1, column=0, padx=15, pady=(0, 20), sticky="nsew")

    def _build_intelligence_ui(self):
        """Sector 5: Neural Intelligence Core."""
        header = ctk.CTkLabel(self.intel_frame, text="Neural Intelligence Core", font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")

        ai_card = self._create_card(self.intel_frame, "🧠 ARTIFICIAL INTELLIGENCE CORE")
        ai_card.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        
        col1 = ctk.CTkFrame(ai_card, fg_color="transparent")
        col1.grid(row=1, column=0, padx=20, pady=20, sticky="ew")
        
        self.provider_var = ctk.StringVar(value=config.LLM_PROVIDER)
        ctk.CTkLabel(col1, text="Primary Intelligence Engine:").grid(row=0, column=0, sticky="w")
        p_menu = ctk.CTkOptionMenu(col1, values=list(self.provider_models.keys()), variable=self.provider_var, command=self.update_provider_visibility)
        p_menu.grid(row=1, column=0, pady=(5, 15), sticky="ew")
        
        self.token_label = ctk.CTkLabel(col1, text="Provider Access Token (Encrypted):")
        self.token_label.grid(row=2, column=0, sticky="w")
        
        self.key_entry = ctk.CTkEntry(col1, show="*", height=40, placeholder_text="sk-...", width=400)
        self.key_entry.grid(row=3, column=0, pady=5, sticky="ew")
        self.key_entry.bind("<KeyRelease>", lambda e: self.save_provider_key())
        self.key_entry.bind("<FocusOut>", lambda e: self.save_provider_key())
        
        ctk.CTkLabel(col1, text="Target Intelligence Model:").grid(row=4, column=0, pady=(15, 0), sticky="w")
        self.model_var = ctk.StringVar(value=self._get_current_model())
        self.model_box = ctk.CTkComboBox(col1, values=self.provider_models.get(config.LLM_PROVIDER, ["default"]), variable=self.model_var, command=self.save_model_choice)
        self.model_box.grid(row=5, column=0, pady=5, sticky="ew")
        self.model_box.bind("<KeyRelease>", lambda e: self.save_model_choice(self.model_var.get()))
        self.model_box.bind("<FocusOut>", lambda e: self.save_model_choice(self.model_var.get()))

        ctk.CTkButton(col1, text="🧪 TEST CONNECTION", height=40, fg_color="#34495e", command=self.test_ai_synapse).grid(row=6, column=0, pady=20, sticky="w")
        
        # Phase 32.5: Email Intelligence Configuration
        em_card = self._create_card(self.intel_frame, "📩 EMAIL DISCOVERY CORE")
        em_card.grid(row=2, column=0, padx=40, pady=10, sticky="ew")
        
        em_inner = ctk.CTkFrame(em_card, fg_color="transparent")
        em_inner.grid(row=1, column=0, padx=25, pady=(0, 20), sticky="ew")
        em_inner.grid_columnconfigure((0, 1), weight=1)
        
        ctk.CTkLabel(em_inner, text="Discovery Email:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w")
        self.em_addr = ctk.CTkEntry(em_inner, height=35, placeholder_text="yourname@yahoo.com")
        self.em_addr.grid(row=1, column=0, padx=(0, 10), pady=5, sticky="ew")
        self.em_addr.insert(0, config.YAHOO_EMAIL or "")
        self.em_addr.bind("<FocusOut>", lambda e: self.save_platform_credentials())

        ctk.CTkLabel(em_inner, text="App-Specific Password:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="w")
        self.em_pass = ctk.CTkEntry(em_inner, height=35, show="*", placeholder_text="xxxx xxxx xxxx xxxx")
        self.em_pass.grid(row=1, column=1, pady=5, sticky="ew")
        self.em_pass.insert(0, config.YAHOO_APP_PASSWORD or "")
        self.em_pass.bind("<FocusOut>", lambda e: self.save_platform_credentials())

        # Phase 38.0: Mission Strategy (Scan Depth)
        ctk.CTkLabel(em_inner, text="Mission Recon Depth (Days Back):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00d4ff").grid(row=2, column=0, pady=(15, 0), sticky="w")
        self.days_slider = ctk.CTkSlider(em_inner, from_=1, to=30, number_of_steps=29, command=self.update_days_label)
        self.days_slider.grid(row=3, column=0, pady=5, sticky="ew")
        self.days_slider.set(config.DAYS_BACK)
        
        self.days_label = ctk.CTkLabel(em_inner, text=f"{int(config.DAYS_BACK)} Days")
        self.days_label.grid(row=3, column=1, padx=10, sticky="w")

        # Phase 30.5: Target Roles Configuration
        ctk.CTkLabel(em_inner, text="Target Search Roles (Comma Separated):", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00d4ff").grid(row=4, column=0, pady=(15, 0), sticky="w")
        self.roles_entry = ctk.CTkEntry(em_inner, height=35, placeholder_text="IT, Developer, Support")
        self.roles_entry.grid(row=5, column=0, columnspan=2, pady=5, sticky="ew")
        self.roles_entry.insert(0, ",".join(config.TARGET_ROLES) if config.TARGET_ROLES else "")
        self.roles_entry.bind("<FocusOut>", lambda e: self.save_mission_strategy())

        ctk.CTkButton(em_inner, text="🧪 TEST EMAIL CONNECTION", height=32, fg_color="#2c3e50", command=self.test_email_discovery).grid(row=6, column=0, pady=(15, 0), sticky="w")

        # Platform Access Control (v30.2.10)
        plat_card = self._create_card(self.intel_frame, "🚀 PLATFORM COMMANDER")
        plat_card.grid(row=4, column=0, padx=40, pady=10, sticky="ew")
        
        plat_inner = ctk.CTkFrame(plat_card, fg_color="transparent")
        plat_inner.grid(row=1, column=0, padx=25, pady=20, sticky="ew")
        plat_inner.grid_columnconfigure((0, 1), weight=1)

        # LinkedIn
        ctk.CTkLabel(plat_inner, text="LinkedIn Email:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=0, sticky="w")
        self.li_email = ctk.CTkEntry(plat_inner, height=35, placeholder_text="email@example.com")
        self.li_email.grid(row=1, column=0, padx=(0, 10), pady=(5, 15), sticky="ew")
        self.li_email.insert(0, config.LINKEDIN_EMAIL or "")
        self.li_email.bind("<KeyRelease>", lambda e: self.save_platform_credentials())

        ctk.CTkLabel(plat_inner, text="LinkedIn Password:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=0, column=1, sticky="w")
        self.li_pass = ctk.CTkEntry(plat_inner, height=35, show="*", placeholder_text="••••••••")
        self.li_pass.grid(row=1, column=1, pady=(5, 15), sticky="ew")
        self.li_pass.insert(0, config.LINKEDIN_PASSWORD or "")
        self.li_pass.bind("<KeyRelease>", lambda e: self.save_platform_credentials())

        # Indeed
        ctk.CTkLabel(plat_inner, text="Indeed Email:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=2, column=0, sticky="w")
        self.in_email = ctk.CTkEntry(plat_inner, height=35, placeholder_text="email@example.com")
        self.in_email.grid(row=3, column=0, padx=(0, 10), pady=(5, 15), sticky="ew")
        self.in_email.insert(0, config.INDEED_EMAIL or "")
        self.in_email.bind("<KeyRelease>", lambda e: self.save_platform_credentials())

        ctk.CTkLabel(plat_inner, text="Indeed Password:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=2, column=1, sticky="w")
        self.in_pass = ctk.CTkEntry(plat_inner, height=35, show="*", placeholder_text="••••••••")
        self.in_pass.grid(row=3, column=1, pady=(5, 15), sticky="ew")
        self.in_pass.insert(0, config.INDEED_PASSWORD or "")
        self.in_pass.bind("<FocusOut>", lambda e: self.save_platform_credentials())

        # ZipRecruiter
        ctk.CTkLabel(plat_inner, text="ZipRecruiter Email:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=4, column=0, sticky="w")
        self.zr_email = ctk.CTkEntry(plat_inner, height=35, placeholder_text="email@example.com")
        self.zr_email.grid(row=5, column=0, padx=(0, 10), pady=(5, 15), sticky="ew")
        self.zr_email.insert(0, config.ZIPRECRUITER_EMAIL or "")
        self.zr_email.bind("<FocusOut>", lambda e: self.save_platform_credentials())

        ctk.CTkLabel(plat_inner, text="ZipRecruiter Password:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=4, column=1, sticky="w")
        self.zr_pass = ctk.CTkEntry(plat_inner, height=35, show="*", placeholder_text="••••••••")
        self.zr_pass.grid(row=5, column=1, pady=(5, 15), sticky="ew")
        self.zr_pass.insert(0, config.ZIPRECRUITER_PASSWORD or "")
        self.zr_pass.bind("<FocusOut>", lambda e: self.save_platform_credentials())

        # Glassdoor
        ctk.CTkLabel(plat_inner, text="Glassdoor Email:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=6, column=0, sticky="w")
        self.gd_email = ctk.CTkEntry(plat_inner, height=35, placeholder_text="email@example.com")
        self.gd_email.grid(row=7, column=0, padx=(0, 10), pady=(5, 15), sticky="ew")
        self.gd_email.insert(0, config.GLASSDOOR_EMAIL or "")
        self.gd_email.bind("<FocusOut>", lambda e: self.save_platform_credentials())

        ctk.CTkLabel(plat_inner, text="Glassdoor Password:", font=ctk.CTkFont(size=11, weight="bold")).grid(row=6, column=1, sticky="w")
        self.gd_pass = ctk.CTkEntry(plat_inner, height=35, show="*", placeholder_text="••••••••")
        self.gd_pass.grid(row=7, column=1, pady=(5, 15), sticky="ew")
        self.gd_pass.insert(0, config.GLASSDOOR_PASSWORD or "")
        self.gd_pass.bind("<FocusOut>", lambda e: self.save_platform_credentials())

        self.update_provider_visibility(config.LLM_PROVIDER)

    def _build_system_core_ui(self):
        """Sector 6: Identity Sovereignty & Maintenance."""
        header = ctk.CTkLabel(self.core_frame, text="System Core & Maintenance", font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")

        # 1. Identity Master
        id_card = self._create_card(self.core_frame, "👤 IDENTITY SOVEREIGN (IDENTITY.YAML)")
        id_card.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        
        ctk.CTkLabel(id_card, text="Your professional identity vault (90+ data points).", text_color="gray").grid(row=1, column=0, padx=25, pady=(10, 0), sticky="w")
        ctk.CTkButton(id_card, text="📝 LAUNCH IDENTITY COMMANDER", height=50, command=self.open_profile_editor).grid(row=2, column=0, padx=25, pady=25, sticky="w")

        # 2. System Maintenance
        maint_card = self._create_card(self.core_frame, "🛠️ MAINTENANCE UTILITIES")
        maint_card.grid(row=2, column=0, padx=40, pady=10, sticky="ew")
        
        m_row = ctk.CTkFrame(maint_card, fg_color="transparent")
        m_row.grid(row=1, column=0, padx=25, pady=20, sticky="w")
        
        ctk.CTkButton(m_row, text="🧹 PURGE OUTPUTS", fg_color="#34495e", command=self.purge_docs).pack(side="left", padx=(0, 15))
        ctk.CTkButton(m_row, text="📜 CLEAN LOGS", fg_color="#34495e", command=self.clean_logs).pack(side="left", padx=(0, 15))
        ctk.CTkButton(m_row, text="🔄 SYNC SYSTEM CODE", fg_color="#27ae60", hover_color="#2ecc71", command=self.run_system_update).pack(side="left")

    def _build_help_ui(self):
        """Sector 7: Help & Support Documentation."""
        header = ctk.CTkLabel(self.help_frame, text="Help & Support Desk", font=ctk.CTkFont(size=28, weight="bold"))
        header.grid(row=0, column=0, padx=40, pady=(40, 20), sticky="w")

        info_card = self._create_card(self.help_frame, f"🛡️ SOVEREIGN AGENT v{config.VERSION}")
        info_card.grid(row=1, column=0, padx=40, pady=10, sticky="ew")
        
        ctk.CTkLabel(info_card, text="The most advanced career automation tool in the world.\nFully autonomous. Fully private. Built for winners.", justify="left").grid(row=1, column=0, padx=25, pady=20, sticky="w")
        
        btn_row = ctk.CTkFrame(info_card, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=25, pady=(0, 25), sticky="w")
        
        ctk.CTkButton(btn_row, text="🌐 OFFICIAL REPOSITORY", command=lambda: webbrowser.open("https://github.com/wisdomgreat/JobAutomation")).pack(side="left", padx=(0, 15))
        ctk.CTkButton(btn_row, text="📖 DOCUMENTATION", fg_color="#34495e", command=lambda: webbrowser.open("https://github.com/wisdomgreat/JobAutomation#readme")).pack(side="left")

    # ─── UI Helper Methods ───
    def _create_card(self, parent, title):
        card = ctk.CTkFrame(parent, corner_radius=15, border_width=1, border_color="#333")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12, weight="bold"), text_color="#00d4ff").grid(row=0, column=0, padx=25, pady=(20, 10), sticky="w")
        card.grid_columnconfigure(0, weight=1)
        return card

    def _create_stat_card(self, parent, title, value, column):
        card = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=12, border_width=1, border_color="#333")
        card.grid(row=0, column=column, padx=8, pady=5, sticky="ew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray").pack(pady=(15, 0))
        val_label = ctk.CTkLabel(card, text=value, font=ctk.CTkFont(size=24, weight="bold"), text_color="#00d4ff")
        val_label.pack(pady=(0, 15))
        return val_label

    # ─── Logic Controllers ───────────────────────────────────────────
    
    def _on_match_slider(self, val):
        """Tactical Controls: Update match intensity threshold."""
        threshold = int(val)
        config.MATCH_SCORE_THRESHOLD = threshold
        self.match_label.configure(text=f"Match Intensity: {threshold}%")
        set_key(str(ENV_PATH), "MATCH_SCORE_THRESHOLD", str(threshold))

    def _on_search_slider(self, val):
        """Tactical Controls: Update search depth per platform."""
        depth = int(val)
        config.MAX_JOBS_PER_SCAN = depth
        self.search_label.configure(text=f"Search Intensity: {depth} jobs")
        set_key(str(ENV_PATH), "MAX_JOBS_PER_SCAN", str(depth))

    def _on_stealth_toggle(self):
        """Tactical Controls: Toggle behavioral stealth (human mimicry delays)."""
        enabled = self.stealth_var.get()
        config.STEALTH_MODE = enabled
        set_key(str(ENV_PATH), "STEALTH_MODE", str(enabled).lower())
        mode = "ACTIVE — Full human mimicry" if enabled else "DISABLED — Speed mode"
        print(f"[Tactical] Behavioral Stealth: {mode}")

    def test_ai_synapse(self):
        """Live connectivity test for the current AI provider."""
        print(f"[System] Initiating AI Synapse handshake via {config.LLM_PROVIDER}...")
        
        def run_test():
            from src.llm_provider import test_connection
            success = test_connection()
            if success:
                print(f"[System] ✓ AI Synapse Online: {config.LLM_PROVIDER} responding normally.")
            else:
                print(f"[System] ✗ AI Synapse Offline: Check your api key or endpoint for {config.LLM_PROVIDER}.")
        
        self._run_in_thread(run_test, name="Synapse Test")

    def run_system_update(self):
        """Sector 6: Seamless mission code synchronization."""
        self._seamless_update()

    def _seamless_update(self):
        """One-click seamless update with progress feedback."""
        print("[Update] Initiating seamless update sequence...")
        
        if hasattr(self, 'update_notif_label'):
            self.update_notif_label.configure(text="⏳ DOWNLOADING UPDATE...", text_color="#f1c40f")
        
        self.status_indic.configure(text="● UPDATING", text_color="#f1c40f")
        self.battery_lvl.configure(progress_color="#f1c40f")
        self.battery_lvl.set(0.0)
        
        def progress_callback(pct):
            try:
                self.after(0, lambda p=pct: self._update_progress(p))
            except: pass
        
        def do_seamless_update():
            try:
                from src.update_manager import check_for_updates, apply_update_seamless, restart_application
                
                # Ensure we have the latest info
                check_for_updates()
                
                result = apply_update_seamless(progress_callback=progress_callback)
                
                if result['success']:
                    self.after(0, lambda: self._update_complete(result))
                elif result.get('message') == "No update available.":
                    self.after(0, lambda: self._update_not_needed())
                else:
                    self.after(0, lambda: self._update_failed(result['message']))
            except Exception as e:
                self.after(0, lambda: self._update_failed(str(e)))
        
        threading.Thread(target=do_seamless_update, daemon=True).start()

    def _update_not_needed(self):
        """Handle case when system is already up to date."""
        self.status_indic.configure(text="● UP TO DATE", text_color="#2ecc71")
        if hasattr(self, 'update_notif_label'):
            self.update_notif_label.configure(text="SYSTEM UP TO DATE", text_color="#2ecc71")

    def _update_progress(self, pct):
        """Update UI progress during download."""
        try:
            self.battery_lvl.set(pct)
            if hasattr(self, 'update_notif_label'):
                self.update_notif_label.configure(text=f"⏳ DOWNLOADING... {int(pct * 100)}%")
        except: pass

    def _update_complete(self, result):
        """Handle successful update."""
        self.battery_lvl.set(1.0)
        self.battery_lvl.configure(progress_color="#2ecc71")
        self.status_indic.configure(text="● UPDATE COMPLETE", text_color="#2ecc71")
        
        if hasattr(self, 'update_notif_label'):
            self.update_notif_label.configure(text="✅ UPDATE INSTALLED — RESTARTING...", text_color="#2ecc71")
        
        print(f"[Update] ✓ {result['message']}")
        
        if result.get('requires_restart'):
            # Give user 3 seconds to see the success message, then restart
            self.after(3000, self._restart_for_update)

    def _update_failed(self, message):
        """Handle failed update."""
        self.battery_lvl.set(1.0)
        self.battery_lvl.configure(progress_color="#e74c3c")
        self.status_indic.configure(text="● UPDATE FAILED", text_color="#e74c3c")
        
        if hasattr(self, 'update_notif_label'):
            self.update_notif_label.configure(text=f"✗ UPDATE FAILED — Click to retry", text_color="#e74c3c")
            self.update_notif_label.bind("<Button-1>", lambda e: self._seamless_update())
        
        print(f"[Update] ✗ {message}")
        # Reset status after 5 seconds
        self.after(5000, lambda: self.status_indic.configure(text="● READY", text_color="#2ecc71"))

    def _restart_for_update(self):
        """Graceful restart after successful update."""
        try:
            from src.update_manager import restart_application
            self.on_closing()  # Clean up stdout redirect
            restart_application()
        except Exception as e:
            print(f"[Update] Please restart the application manually. ({e})")

    def stop_pipeline(self):
        print("[System] EMERGENCY ALL-STOP SIGNALED. Shutting down browser engines.")
        self.status_indic.configure(text="● ABORTED", text_color="#e74c3c")
        self.battery_lvl.configure(progress_color="#e74c3c")

    def refresh_stats(self):
        if not self.winfo_exists(): return
        try:
            # Phase 36.2: Pulse Sync Readiness
            self.update_readiness_ui()
            
            stats = self.tracker.get_stats()
            self.stat_apps.configure(text=str(stats.get('applied', 0)))
            self.stat_interviews.configure(text=str(stats.get('interviews', 0)))
            self.stat_discoveries.configure(text=str(stats.get('total', 0)))
            rate = (stats.get('applied', 0) / max(1, stats.get('total', 0))) * 100
            self.stat_success.configure(text=f"{rate:.0f}%")
            
            self._update_funnel_chart(stats)
            self._update_pie_chart(stats)
        except Exception as e: 
            print(f"[Error] Stats refresh failed: {e}")

    def _update_funnel_chart(self, stats):
        """Premium funnel visualization with gradient bars and analytics."""
        try:
            if not self.funnel_canvas.winfo_exists(): return
            self.funnel_canvas.delete("all")
            self.funnel_canvas.update_idletasks()
            w = max(self.funnel_canvas.winfo_width(), 360)
            h = max(self.funnel_canvas.winfo_height(), 220)
            
            stages = [
                ("DISCOVERY", stats.get('total', 0), "#1e6f9f", "#00d4ff"),
                ("APPLIED", stats.get('applied', 0), "#1a6b33", "#2ecc71"),
                ("INTERVIEW", stats.get('interviews', 0), "#6c2d91", "#a855f7"),
                ("OFFER", stats.get('offers', 0), "#b8860b", "#f1c40f")
            ]
            
            max_val = max(1, sum(s[1] for s in stages)) # Total items for scaling
            bar_height = 34
            spacing = 14
            total_chart_h = len(stages) * (bar_height + spacing) - spacing
            start_y = (h - total_chart_h) / 2
            left_margin = 110
            right_margin = 65
            max_bar_width = w - left_margin - right_margin
            
            # If nothing in funnel, show "Ghost" empty state
            is_empty = all(s[1] == 0 for s in stages)
            
            for i, (name, val, dark_color, bright_color) in enumerate(stages):
                y0 = max(start_y + i * (bar_height + spacing), 20)
                y1 = y0 + bar_height
                
                # Background track (subtle)
                self.funnel_canvas.create_rectangle(
                    left_margin, y0, left_margin + max_bar_width, y1,
                    fill="#1a1e26", outline="#2a2e36", width=1
                )
                
                # Filled bar
                if is_empty:
                    ratio = 0
                    bar_w = 0
                else:
                    ratio = val / max(1, stages[0][1]) # Proportion of Discovery
                    bar_w = max(max_bar_width * ratio, 4 if val > 0 else 0)
                
                if bar_w > 0:
                    # Main bar
                    self.funnel_canvas.create_rectangle(
                        left_margin, y0, left_margin + bar_w, y1,
                        fill=dark_color, outline=""
                    )
                    # Bright tip accent (last 3px glow)
                    tip_x = left_margin + bar_w
                    self.funnel_canvas.create_rectangle(
                        max(tip_x - 3, left_margin), y0, tip_x, y1,
                        fill=bright_color, outline=""
                    )
                
                # Stage label (left)
                self.funnel_canvas.create_text(
                    left_margin - 15, (y0 + y1) / 2,
                    text=name, fill="#8b949e" if is_empty else "white", 
                    font=("Inter", 9, "bold"), anchor="e"
                )
                
                # Value count (right of bar)
                val_text = str(val) if not is_empty else "--"
                self.funnel_canvas.create_text(
                    left_margin + max_bar_width + 15, (y0 + y1) / 2,
                    text=val_text, fill=bright_color if not is_empty else "#30363d", 
                    font=("Inter", 12, "bold"), anchor="w"
                )
                
                # Percentage inside bar (if wide enough)
                if bar_w > 60 and pct_text:
                    self.funnel_canvas.create_text(
                        left_margin + bar_w - 8, (y0 + y1) / 2,
                        text=pct_text, fill="white", font=("Inter", 9), anchor="e"
                    )
        except: pass

    def _update_pie_chart(self, stats):
        """Premium donut chart with legend and center stat."""
        try:
            if not self.pie_canvas.winfo_exists(): return
            self.pie_canvas.delete("all")
            self.pie_canvas.update_idletasks()
            w = max(self.pie_canvas.winfo_width(), 360)
            h = max(self.pie_canvas.winfo_height(), 220)
            
            platforms = stats.get('platforms', {})
            if not platforms:
                self.pie_canvas.create_text(w/2, h/2 - 10, text="NO PLATFORM DATA YET", 
                                            fill="#4a5568", font=("Inter", 12, "bold"))
                self.pie_canvas.create_text(w/2, h/2 + 12, text="Run a search to populate", 
                                            fill="#2d3748", font=("Inter", 10))
                return
                
            total = sum(platforms.values())
            if total == 0: return
            
            colors = ["#2ecc71", "#00d4ff", "#a855f7", "#f1c40f", "#e67e22", "#e74c3c", "#3b82f6", "#ec4899"]
            
            # Donut chart (left half of canvas)
            cx = w * 0.32
            cy = h * 0.42
            outer_r = min(w * 0.22, h * 0.38)
            inner_r = outer_r * 0.55
            
            start_angle = 90
            segments = []
            
            for i, (plat, count) in enumerate(platforms.items()):
                extent = (count / total) * 360
                color = colors[i % len(colors)]
                
                # Outer arc
                self.pie_canvas.create_arc(
                    cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r,
                    start=start_angle, extent=extent, fill=color, outline="#0d1117", width=2
                )
                
                segments.append((plat, count, color, start_angle, extent))
                start_angle += extent
            
            # Inner circle (creates donut hole)
            self.pie_canvas.create_oval(
                cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r,
                fill="#0d1117", outline="#0d1117"
            )
            
            # Center stat
            self.pie_canvas.create_text(cx, cy - 8, text=str(total),
                                         fill="#00d4ff", font=("Inter", 20, "bold"))
            self.pie_canvas.create_text(cx, cy + 12, text="TOTAL",
                                         fill="#4a5568", font=("Inter", 8, "bold"))
            
            # Legend (right side)
            legend_x = w * 0.60
            legend_y_start = cy - (len(platforms) * 22) / 2
            
            for i, (plat, count, color, _, _) in enumerate(segments):
                ly = legend_y_start + i * 24
                pct = (count / total * 100)
                
                # Color dot
                dot_r = 5
                self.pie_canvas.create_oval(
                    legend_x, ly - dot_r, legend_x + dot_r * 2, ly + dot_r,
                    fill=color, outline=""
                )
                
                # Platform name
                self.pie_canvas.create_text(
                    legend_x + 16, ly,
                    text=plat, fill="#c9d1d9", font=("Inter", 10), anchor="w"
                )
                
                # Count + percentage
                self.pie_canvas.create_text(
                    w - 20, ly,
                    text=f"{count}  ({pct:.0f}%)", fill="#8b949e", font=("Inter", 9), anchor="e"
                )
        except Exception: pass

    def refresh_crm_feed(self):
        """Sector 4: Real-time candidate tracking synchronization."""
        if not self.winfo_exists() or self._current_frame_name != "CRM": return
        # Clear existing feed safely
        try:
            for w in self.feed_scroll.winfo_children(): w.destroy()
        except: pass
        
        # Load targets from tracker.db
        jobs = self.tracker.get_pending_reviews()
        if not jobs:
            ctk.CTkLabel(self.feed_scroll, text="No active mission targets detected.", text_color="gray").pack(pady=40)
        else:
            for job in jobs[:50]: # Show top 50
                self._create_job_row(self.feed_scroll, job, is_history=False)

    def _create_job_row(self, parent, job, is_history=False):
        row = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=10)
        # Strategic Reminder: Highlight if outreach was > 3 days ago with no reply (Placeholder logic)
        row.pack(fill="x", pady=4, padx=5)
        
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(content, text=job['job_title'], font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(content, text=f"{job['company']} • {job['location']} • {job['source']}", font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w")
        
        # Match Reason (v32.9 Transparency)
        reason = job.get('match_reason') or ""
        if reason:
            ctk.CTkLabel(content, text=f"🤖 {reason}", font=ctk.CTkFont(size=10, slant="italic"), text_color="#2ecc71").pack(anchor="w", pady=(2, 0))
        score_color = "#2ecc71" if job.get('match_score',0) > 80 else "#f1c40f" if job.get('match_score',0) > 60 else "#e67e22"
        ctk.CTkLabel(row, text=f"{job.get('match_score',0)}%", text_color=score_color, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=20)
        
        if not is_history:
            # Action Cluster
            actions = ctk.CTkFrame(row, fg_color="transparent")
            actions.pack(side="right", padx=10)
            
            # 👤 Recruiter Discovery Link (v34.0)
            if job.get('hiring_manager'):
                ctk.CTkLabel(actions, text=f"👤 {job['hiring_manager']}", font=ctk.CTkFont(size=11), text_color="#00d4ff", cursor="hand2").pack(side="left", padx=5)
            
            # 👻 Ghost Detection Flag (v34.0)
            if job.get('posted_date') and "days ago" in job['posted_date']:
                days = int(''.join(filter(str.isdigit, job['posted_date'])))
                if days > 60:
                    ctk.CTkLabel(actions, text="👻 GHOST", font=ctk.CTkFont(size=10, weight="bold"), text_color="#e74c3c").pack(side="left", padx=5)

            ctk.CTkButton(actions, text="APPLY", width=70, height=28, fg_color="#2980b9", command=lambda j=job: self._quick_apply_logic(j)).pack(side="left", padx=5)
            # Log Outreach (v32.9)
            ctk.CTkButton(actions, text="💬 LOG", width=55, height=28, fg_color="#34495e", command=lambda j=job: self._show_outreach_modal(j)).pack(side="left", padx=5)
            ctk.CTkButton(actions, text="✅", width=35, height=28, fg_color="#27ae60", command=lambda j=job: self._mark_applied_logic(j)).pack(side="left", padx=5)
            ctk.CTkButton(actions, text="🗑️", width=35, height=28, fg_color="#c0392b", command=lambda j=job: self._delete_job_logic(j)).pack(side="left", padx=5)

    def refresh_stats_loop(self):
        """Active Mission Monitoring: Runs every 5s while Dashboard is active."""
        if not self.winfo_exists(): return
        
        # Phase 35.5: Defensive State Verification
        if not hasattr(self, "_current_frame_name"): return
        
        # Ultimate Stability Guard: Wrapped in try-except to handle 
        # race conditions where 'self' becomes a 'tkapp' object during destruction.
        try:
            if hasattr(self, "_current_frame_name") and self._current_frame_name == "Dashboard":
                self.refresh_stats()
        except (AttributeError, RuntimeError):
            return
        
        self.after(5000, self.refresh_stats_loop)

    def run_surgical_apply(self, only_docs=False):
        """Sector 2: Precision Striking."""
        url = self.surgical_url_entry.get().strip()
        if not url:
            import tkinter.messagebox
            tkinter.messagebox.showwarning("Target Required", "Please enter a valid job URL before generating an asset kit or applying.")
            return
        
        guided = self.guided_var.get()
        # Phase 32.3: Platform Override Logic
        plat_choice = self.strike_plat_var.get()
        override_plat = None if plat_choice == "Auto-Detect" else plat_choice.lower()
        
        print(f"[Operation] Initiating sovereign surgical strike on: {url}" + (" (DOCS ONLY)" if only_docs else ""))
        
        def run_strike():
            try:
                from src.applicant_bot import apply_to_job, extract_job_details
                from src.resume_builder import generate_documents, parse_resume

                # 1. INTELLIGENCE EXTRACTION
                print("[Intelligence] Extracting mission coordinates from target page...")
                jd_details = extract_job_details(url)
                
                if not jd_details["description"]:
                    print("[Warning] Failed to extract full job description. Using base resume for generic apply.")
                    resume_path = str(config.BASE_RESUME_PDF)
                    resume_text = ""
                else:
                    # 2. DOCUMENT TAILORING
                    print(f"[Strategy] Tailoring assets for {jd_details['title']} at {jd_details['company']}...")
                    paths = generate_documents(
                        job_title=jd_details["title"],
                        company=jd_details["company"],
                        location=jd_details.get("location", "Remote"),
                        job_description=jd_details["description"]
                    )
                    resume_path = str(paths["resume_pdf"])
                    
                    # Store resume text for LLM question answering
                    try: resume_text = parse_resume(paths["resume_pdf"])
                    except: resume_text = ""

                if only_docs:
                    print(f"[Success] Surgical tailoring complete. Assets saved to {Path(resume_path).parent}")
                    return

                # 3. PRECISION APPLICATION
                print(f"[Execution] Launching apply pipeline" + (" in GUIDED MODE" if guided else "") + "...")
                result = apply_to_job(
                    url, 
                    resume_path=resume_path, 
                    resume_text=resume_text,
                    guided=guided
                )
                print(f"[Operation] Result: {result['message']}")
                
                if result.get("success"):
                    self.after(0, self.refresh_stats)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[Error] Surgical strike failed: {e}")
                
        self._run_in_thread(run_strike, name="Surgical Apply")
        self.select_frame_by_name("Dashboard")

    def open_profile_editor(self):
        """Launches the high-density Identity Sovereign Editor."""
        ProfileEditorWindow(self)

    def show_search_form(self):
        """Invoke the Search Matrix Configuration window."""
        SearchWindow(self)

    def run_full_pipeline(self):
        """Parity: Full Pipeline (100% Auto)."""
        # Phase 36.1: Readiness Gate
        ai_ok, id_ok, res_ok = self.get_mission_status()
        if not (ai_ok and id_ok and res_ok):
            print("\n[Security] ✗ MISSION ABORTED: Readiness Checklist Incomplete.")
            print("[Security] Ensure AI, Identity, and Resume are properly configured.")
            return

    def run_full_pipeline(self):
        """Phase 25.0: Direct CLI Orchestration via Thread."""
        # Force config refresh from .env before mission start
        config.reload_from_env()
        
        print("[Operation] INITIATING FULL AUTO-PIPELINE (Autonomous Mode)...")
        
        def run_pipe():
            from main import run_auto_pipeline
            run_auto_pipeline(days_back=float(config.DAYS_BACK))
            self.refresh_stats()
            
        self._run_in_thread(run_pipe, name="Full Pipeline")
        self.select_frame_by_name("Dashboard")

    def run_email_scan(self):
        """Parity: Scan Email Alerts with Platform Filtering."""
        def launch_scan(platforms):
            print(f"[Intelligence] Commencing inbox scan for: {platforms}...")
            def run_scan():
                from src.email_scanner import EmailScanner
                scanner = EmailScanner()
                # Pass allowed_platforms and mission depth (DAYS_BACK) to scanning logic
                alerts = scanner.scan(days_back=float(config.DAYS_BACK), filter_roles=bool(config.TARGET_ROLES), allowed_platforms=platforms)
                scanner.disconnect()
                
                if not alerts:
                    print("[Intelligence] No new job alerts found.")
                    return
                
                print(f"[Intelligence] Identified {len(alerts)} valid job targets. Syncing to tracker...")
                for alert in alerts:
                    # Skip if bot manager doesn't handle it
                    try:
                        # Surgical Fix: get_bot expects (url, platform), profile is handled internally
                        bot = get_bot(alert.apply_url, platform=alert.source.lower())
                        if not bot: continue
                    except: continue
                    
                    self.tracker.add(
                        job_title=alert.job_title,
                        company=alert.company,
                        location=alert.location,
                        description=alert.description,
                        apply_url=alert.apply_url,
                        source=alert.source,
                        match_score=alert.match_score,
                    )
                self.after(0, self.refresh_crm_feed)
                self.after(0, self.refresh_stats)
                
            self._run_in_thread(run_scan, name="Email Scan")
        
        # Phase 32.3: Launch Filter Dialog
        EmailScanDialog(self, launch_scan)
        self.select_frame_by_name("Dashboard")

    def _show_help_center(self):
        """Sector 7: Built-in Onboarding & Setup Intelligence."""
        HelpCenterWindow(self)

    def _show_outreach_modal(self, job):
        """Parity: Tactical Search."""
        OutreachWindow(self, job)

    def update_provider_visibility(self, provider):
        """Dynamic UI adjustment for Local vs Cloud brains."""
        # 1. Save whatever is currently in the entry before switching
        current_p = config.LLM_PROVIDER
        if hasattr(self, 'key_entry') and not self._initializing:
            self.provider_keys[current_p] = self.key_entry.get()

        set_key(str(ENV_PATH), "LLM_PROVIDER", provider)
        config.LLM_PROVIDER = provider
        
        # Toggle label
        is_local = provider in ["ollama", "lmstudio"]
        self.token_label.configure(text="Local Endpoint URL:" if is_local else "Provider Access Token (Encrypted):")
        self.key_entry.configure(show="" if is_local else "*", placeholder_text="http://localhost:..." if is_local else "sk-...")
        
        # Update entry content
        self.key_entry.delete(0, "end")
        self.key_entry.insert(0, self.provider_keys.get(provider, ""))
        
        # Update model list
        models = self.provider_models.get(provider, ["default"])
        self.model_box.configure(values=models)
        
        # Get correct model for this provider (from config)
        current_model = self._get_current_model_for_provider(provider)
        self.model_var.set(current_model)

    def _get_current_model(self):
        return self._get_current_model_for_provider(config.LLM_PROVIDER)

    def _get_current_model_for_provider(self, p):
        if p == "openai": return config.OPENAI_MODEL or "gpt-4o"
        if p == "gemini": return config.GEMINI_MODEL or "gemini-2.0-flash"
        if p == "claude": return config.ANTHROPIC_MODEL or "claude-3-5-sonnet-20240620"
        if p == "ollama": return config.OLLAMA_MODEL or "llama3"
        if p == "lmstudio": return config.LMSTUDIO_MODEL or "default"
        if p == "groq": return config.GROQ_MODEL or "llama-3.1-70b-versatile"
        if p == "openrouter": return config.OPENROUTER_MODEL or "google/gemini-2.0-flash-001"
        return "default"

    def save_model_choice(self, model):
        p = config.LLM_PROVIDER
        key = f"{p.upper()}_MODEL"
        if p == "claude": key = "ANTHROPIC_MODEL"
        if p == "lmstudio": key = "LMSTUDIO_MODEL"
        
        set_key(str(ENV_PATH), key, model)
        # Update run-time config
        if p == "openai": config.OPENAI_MODEL = model
        elif p == "gemini": config.GEMINI_MODEL = model
        elif p == "claude": config.ANTHROPIC_MODEL = model
        elif p == "ollama": config.OLLAMA_MODEL = model
        elif p == "lmstudio": config.LMSTUDIO_MODEL = model
        elif p == "groq": config.GROQ_MODEL = model
        elif p == "openrouter": config.OPENROUTER_MODEL = model

    def save_provider_key(self):
        """Persistence Engine: Synchronizes UI entries with .env and run-time config."""
        p = self.provider_var.get()
        val = self.key_entry.get()
        
        # Update local cache
        self.provider_keys[p] = val
        
        # Determine .env keys and update memory config
        env_key = ""
        if p == "openai": 
            env_key = "OPENAI_API_KEY"
            config.OPENAI_API_KEY = val
        elif p == "gemini":
            env_key = "GEMINI_API_KEY"
            config.GEMINI_API_KEY = val
        elif p == "claude":
            env_key = "ANTHROPIC_API_KEY"
            config.ANTHROPIC_API_KEY = val
        elif p == "groq":
            env_key = "GROQ_API_KEY"
            config.GROQ_API_KEY = val
        elif p == "ollama":
            env_key = "OLLAMA_BASE_URL"
            config.OLLAMA_BASE_URL = val
        elif p == "lmstudio":
            env_key = "LMSTUDIO_BASE_URL"
            config.LMSTUDIO_BASE_URL = val
        elif p == "openrouter":
            env_key = "OPENROUTER_API_KEY"
            config.OPENROUTER_API_KEY = val
            
        if env_key:
            set_key(str(ENV_PATH), env_key, val)

    def save_platform_credentials(self):
        """Strategic Sync: Persist Platform Credentials and Mission Strategy to .env."""
        if self._initializing: return
        
        creds = {
            "LINKEDIN_EMAIL": self.li_email.get(),
            "LINKEDIN_PASSWORD": self.li_pass.get(),
            "INDEED_EMAIL": self.in_email.get(),
            "INDEED_PASSWORD": self.in_pass.get(),
            "ZIPRECRUITER_EMAIL": self.zr_email.get(),
            "ZIPRECRUITER_PASSWORD": self.zr_pass.get(),
            "GLASSDOOR_EMAIL": self.gd_email.get(),
            "GLASSDOOR_PASSWORD": self.gd_pass.get(),
            "YAHOO_EMAIL": self.em_addr.get(),
            "YAHOO_APP_PASSWORD": self.em_pass.get(),
            "DAYS_BACK": str(int(self.days_slider.get()))
        }
        
        for key, val in creds.items():
            set_key(str(ENV_PATH), key, val)
            setattr(config, key, val) # Update runtime config

    def update_days_label(self, val):
        self.days_label.configure(text=f"{int(val)} Days")
        self.save_platform_credentials()

    def upload_master_resume(self):
        """Tactical Injection: Overwrite base resume in permanent storage."""
        file_path = filedialog.askopenfilename(
            title="Select Master Resume",
            filetypes=[("Resume Files", "*.pdf *.docx"), ("All Files", "*.*")]
        )
        
        if not file_path: return
        
        ext = Path(file_path).suffix.lower()
        target = config.BASE_RESUME_PDF if ext == ".pdf" else config.BASE_RESUME_DOCX
        
        try:
            # Delete old versions to prevent confusion
            if config.BASE_RESUME_PDF.exists(): config.BASE_RESUME_PDF.unlink()
            if config.BASE_RESUME_DOCX.exists(): config.BASE_RESUME_DOCX.unlink()
            
            shutil.copy2(file_path, target)
            messagebox.showinfo("Success", f"Master Resume successfully injected into {target.name}")
            self.update_readiness_ui()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload resume: {e}")

    def update_match_label(self, val):
        config.MATCH_SCORE_THRESHOLD = int(val)
        self.match_label.configure(text=f"Match Threshold: {int(val)}%")

    def _quick_apply_logic(self, job):
        """Targeted strike trigger: Transfer to Surgical Apply Engine."""
        url = job.get('apply_url')
        if not url: return
        
        print(f"[Operation] Initiating 'Quick Apply' for target: {job['job_title']}...")
        # Populate the entry and trigger the strike
        self.surgical_url_entry.delete(0, "end")
        self.surgical_url_entry.insert(0, url)
        self.run_surgical_apply()

    def _mark_applied_logic(self, job):
        """Manual status override."""
        print(f"[System] Marking {job['job_title']} as APPLIED.")
        self.tracker.update_status(job['id'], 'applied')
        self.refresh_crm_feed()
        self.refresh_stats()

    def _delete_job_logic(self, job):
        """Surgical termination with confirmation safety gate."""
        msg = f"Permanently terminate mission target '{job['job_title']}' at {job['company']}?\nThis action cannot be undone."
        if messagebox.askyesno("Confirm Termination", msg):
            self.tracker.delete(job['id'])
            self.refresh_crm_feed()
            self.refresh_stats()
            print(f"[System] Target terminated successfully.")

    def purge_docs(self):
        """Maintenance: Purge mission documents."""
        print("[System] Initiating document purge...")
        try:
            from src.maintenance import purge_old_outputs
            deleted, space = purge_old_outputs(days=0)
            print(f"[System] Success! Removed {deleted} folders, freeing {space} MB.")
        except Exception as e:
            print(f"[Error] Purge failed: {e}")
    
    def clean_logs(self):
        """Maintenance: Clean system logs."""
        print("[System] Scrubbing log archives...")
        try:
            log_dir = DATA_DIR / "logs"
            if log_dir.exists():
                count = 0
                for f in log_dir.glob("*"):
                    if f.is_file():
                        f.unlink()
                        count += 1
                print(f"[System] Cleanup complete. {count} log files terminated.")
            else:
                print("[System] Log directory not found.")
        except Exception as e:
            print(f"[Error] Log cleanup failed: {e}")

    def enable_redirection(self):
        if hasattr(self, 'log_box'):
            sys.stdout = LogRedirector(self.log_box)
            print("[System] Sovereign Console Online. Terminal handshake complete.")

    def get_mission_status(self):
        """High-fidelity scan of system readiness parameters."""
        # 1. AI Check
        ai_key = self.provider_keys.get(config.LLM_PROVIDER, "")
        ai_ready = len(str(ai_key)) > 5
        
        # 2. Identity Check (Uses centralized profile instance)
        name = self.profile.data.get("personal", {}).get("first_name", "")
        email = self.profile.data.get("personal", {}).get("email", "")
        id_ready = len(name) > 1 and len(email) > 3
        
        # 3. Resume Check (Cross-platform path resolution)
        # We use .resolve() to ensure OS-agnostic path comparison if needed
        res_ready = config.BASE_RESUME_PDF.exists() or config.BASE_RESUME_DOCX.exists()
        
        return ai_ready, id_ready, res_ready

    def update_readiness_ui(self):
        """Synchronize the Dashboard checklist with actual system state."""
        if not hasattr(self, "ready_ai"): return
        
        ai, ident, res = self.get_mission_status()
        
        self.ready_ai.configure(text=f"{'✅' if ai else '○'} AI Synapse", text_color="#2ecc71" if ai else "gray")
        self.ready_id.configure(text=f"{'✅' if ident else '○'} Identity Sync", text_color="#2ecc71" if ident else "gray")
        self.ready_resume.configure(text=f"{'✅' if res else '○'} Master Resume", text_color="#2ecc71" if res else "gray")

    def check_onboarding(self):
        # Initial scan to populate UI
        self.update_readiness_ui()

    def on_closing(self):
        sys.stdout = self._old_stdout
        self.quit()


class ProfileEditorWindow(ctk.CTkToplevel):
    """Identity Sovereign 2.0: Deep-profile editor for 90+ professional data points."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Identity Sovereign Commander")
        self.geometry("1100x850")
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.profile = ApplicantProfile()
        self.controls = {} # Store widget references for saving
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(30, 10))
        ctk.CTkLabel(header, text="IDENTITY COMMANDER", font=ctk.CTkFont(size=24, weight="bold"), text_color="#00d4ff").pack(side="left")
        ctk.CTkLabel(header, text="v2.8 Deep Sync", text_color="gray").pack(side="left", padx=15, pady=(5,0))

        # Main Hub
        self.tabs = ctk.CTkTabview(self, segmented_button_selected_color="#00d4ff", segmented_button_selected_hover_color="#00b8e6", segmented_button_unselected_color="#1a1a1a")
        self.tabs.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Tab Definitions
        self.tab_names = ["Personal", "Work Auth", "Experience", "Preferences", "Skills", "Demographics"]
        for name in self.tab_names: self.tabs.add(name)
        
        self._build_personal()
        self._build_work_auth()
        self._build_experience()
        self._build_preferences()
        self._build_skills()
        self._build_demographics()
        
        # Action Bar
        action_bar = ctk.CTkFrame(self, fg_color="transparent")
        action_bar.pack(fill="x", padx=30, pady=30)
        
        self.save_btn = ctk.CTkButton(action_bar, text="💾 SAVE & SYNC MASTER IDENTITY", height=50, width=300, 
                                      fg_color="#27ae60", hover_color="#2ecc71", font=ctk.CTkFont(weight="bold"), command=self.save)
        self.save_btn.pack(side="right")
        
        ctk.CTkButton(action_bar, text="✖ CANCEL", height=50, width=120, fg_color="#34495e", command=self.destroy).pack(side="right", padx=15)

    def _create_field(self, parent, label, key, section, row, is_long=False, options=None, is_bool=False):
        """Dynamic high-fidelity field creator."""
        ctk.CTkLabel(parent, text=label, font=ctk.CTkFont(size=12, weight="bold")).grid(row=row, column=0, padx=20, pady=8, sticky="w")
        
        val = self.profile.data.get(section, {}).get(key, "")
        
        if is_bool:
            var = tk.BooleanVar(value=bool(val))
            widget = ctk.CTkSwitch(parent, text="", variable=var, progress_color="#00d4ff")
            widget.grid(row=row, column=1, padx=20, pady=8, sticky="w")
            self.controls[(section, key)] = var
        elif options:
            var = ctk.StringVar(value=str(val))
            widget = ctk.CTkOptionMenu(parent, values=options, variable=var, width=300)
            widget.grid(row=row, column=1, padx=20, pady=8, sticky="w")
            self.controls[(section, key)] = var
        elif is_long:
            widget = ctk.CTkTextbox(parent, height=100, width=500, font=("Inter", 12))
            widget.insert("1.0", str(val))
            widget.grid(row=row, column=1, padx=20, pady=8, sticky="ew")
            self.controls[(section, key)] = widget
        else:
            widget = ctk.CTkEntry(parent, width=500, height=35)
            widget.insert(0, str(val))
            widget.grid(row=row, column=1, padx=20, pady=8, sticky="ew")
            self.controls[(section, key)] = widget

    def _build_personal(self):
        sc = ctk.CTkScrollableFrame(self.tabs.tab("Personal"), fg_color="transparent")
        sc.pack(fill="both", expand=True)
        sc.grid_columnconfigure(1, weight=1)
        
        fields = [
            ("first_name", "First Name"), ("middle_name", "Middle Name"), ("last_name", "Last Name"),
            ("preferred_name", "Preferred / Display Name"), ("email", "Contact Email"),
            ("phone", "Phone Number"), ("phone_prefix", "Country Code (+1)"),
            ("city", "City"), ("province", "State / Province"), ("country", "Country"),
            ("linkedin_url", "LinkedIn URL"), ("github_url", "GitHub URL"), ("portfolio_url", "Portfolio URL")
        ]
        for i, (k, l) in enumerate(fields):
            self._create_field(sc, l, k, "personal", i)

    def _build_work_auth(self):
        sc = ctk.CTkScrollableFrame(self.tabs.tab("Work Auth"), fg_color="transparent")
        sc.pack(fill="both", expand=True)
        self._create_field(sc, "Are you authorized to work in your target country?", "authorized_to_work", "work_authorization", 0, is_bool=True)
        self._create_field(sc, "Will you require visa sponsorship?", "sponsorship_needed", "work_authorization", 1, is_bool=True)
        self._create_field(sc, "Specific Work Permit Type", "work_permit_type", "work_authorization", 2, options=["None", "Citizen", "PR", "Work Permit", "H1-B", "Other"])

    def _build_experience(self):
        sc = ctk.CTkScrollableFrame(self.tabs.tab("Experience"), fg_color="transparent")
        sc.pack(fill="both", expand=True)
        sc.grid_columnconfigure(1, weight=1)
        self._create_field(sc, "Total Years of Experience", "total_years", "experience", 0)
        self._create_field(sc, "Most Recent Job Title", "current_title", "experience", 1)
        self._create_field(sc, "Global Professional Summary", "summary", "experience", 2, is_long=True)

    def _build_preferences(self):
        sc = ctk.CTkScrollableFrame(self.tabs.tab("Preferences"), fg_color="transparent")
        sc.pack(fill="both", expand=True)
        self._create_field(sc, "Willing to Relocate?", "willing_to_relocate", "preferences", 0, is_bool=True)
        self._create_field(sc, "Salary Expectation / Range", "salary_expectation", "preferences", 1)
        self._create_field(sc, "Employment Type", "work_type", "preferences", 2, options=["Full-time", "Contract", "Part-time"])
        self._create_field(sc, "Work Mode Preference", "remote_preference", "preferences", 3, options=["Remote", "Hybrid", "Onsite"])

    def _build_skills(self):
        sc = ctk.CTkScrollableFrame(self.tabs.tab("Skills"), fg_color="transparent")
        sc.pack(fill="both", expand=True)
        self._create_field(sc, "Technical Skills Stack", "technical", "skills", 0, is_long=True)
        self._create_field(sc, "Soft Skills / Leadership", "soft", "skills", 1, is_long=True)

    def _build_demographics(self):
        sc = ctk.CTkScrollableFrame(self.tabs.tab("Demographics"), fg_color="transparent")
        sc.pack(fill="both", expand=True)
        self._create_field(sc, "Gender", "gender", "demographics", 0, options=["Male", "Female", "Non-binary", "Decline to self-identify"])
        self._create_field(sc, "Ethnicity", "ethnicity", "demographics", 1)
        self._create_field(sc, "Veteran Status", "veteran", "demographics", 2, options=["No", "Yes", "Decline to self-identify"])

    def save(self):
        """Recursive sync of GUI controls back to Master Profile."""
        for (section, key), widget in self.controls.items():
            if isinstance(widget, (ctk.CTkEntry, ctk.StringVar, tk.BooleanVar)):
                self.profile.data[section][key] = widget.get()
            elif isinstance(widget, ctk.CTkTextbox):
                self.profile.data[section][key] = widget.get("1.0", "end").strip()
                
        self.profile.save()
        print("[Identity] MASTER SYNC SUCCESSFUL. profile.yaml updated.")
        self.destroy()

    def on_closing(self):
        self.grab_release()
        self.destroy()

class SearchWindow(ctk.CTkToplevel):
    """Tactical Search Configuration Modal."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Tactical Search Matrix")
        self.geometry("600x400")
        self.transient(parent)
        self.grab_set()
        
        ctk.CTkLabel(self, text="JOB DISCOVERY MATRIX", font=ctk.CTkFont(size=20, weight="bold"), text_color="#2ecc71").pack(pady=20)
        
        self.key_entry = ctk.CTkEntry(self, placeholder_text="Search Keywords (e.g. Python Remote)...", height=45, width=400)
        self.key_entry.pack(pady=10)
        
        self.loc_entry = ctk.CTkEntry(self, placeholder_text="Location / Region...", height=45, width=400)
        self.loc_entry.pack(pady=10)
        
        # Phase 32.3: Multi-Platform Selection Matrix
        plat_frame = ctk.CTkFrame(self, fg_color="transparent")
        plat_frame.pack(pady=10)
        
        self.plat_vars = {}
        platforms = ["LinkedIn", "Indeed", "ZipRecruiter", "Dice", "Wellfound", "BuiltIn"]
        for i, plat in enumerate(platforms):
            var = ctk.BooleanVar(value=True if plat in ["LinkedIn", "Indeed"] else False)
            cb = ctk.CTkCheckBox(plat_frame, text=plat, variable=var, font=ctk.CTkFont(size=12))
            cb.grid(row=i//3, column=i%3, padx=15, pady=5, sticky="w")
            self.plat_vars[plat] = var
            
        ctk.CTkButton(self, text="⚡ INITIATE TACTICAL SCAN", height=50, width=200, fg_color="#27ae60", command=self.search).pack(pady=20)

    def search(self):
        keywords = self.key_entry.get()
        location = self.loc_entry.get() or "Remote"
        
        # Phase 32.3: Collect selected platforms
        selected_plats = [p for p, v in self.plat_vars.items() if v.get()]
        if not selected_plats: selected_plats = ["LinkedIn", "Indeed"]
        
        print(f"[Tactical] Launching matrix search for: {keywords} on {selected_plats}")
        
        def run_matrix():
            from main import run_search_pipeline
            # run_search_pipeline currently only supports "both" or single; 
            # we will iterate through selected platforms sequentially for stability
            for plat in selected_plats:
                run_search_pipeline(platform=plat.lower(), keywords=keywords, locations=[location], limit=config.MAX_JOBS_PER_SCAN)
            
            self.master.refresh_crm_feed()
            
        self.master._run_in_thread(run_matrix, name="Search Matrix")
        self.destroy()


class OutreachWindow(ctk.CTkToplevel):
    """Strategic Outreach Terminal: Track networking efforts."""
    def __init__(self, parent, job):
        super().__init__(parent)
        self.parent = parent
        self.job = job
        self.title(f"Log Outreach: {job['company']}")
        self.geometry("500x550")
        self.transient(parent)
        self.grab_set()
        
        ctk.CTkLabel(self, text="STRATEGIC OUTREACH LOG", font=ctk.CTkFont(size=18, weight="bold"), text_color="#00d4ff").pack(pady=20)
        
        # Form Fields
        ctk.CTkLabel(self, text="Communication Type", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=40)
        self.type_var = ctk.StringVar(value="LinkedIn Message")
        ctk.CTkOptionMenu(self, values=["LinkedIn Message", "Cold Email", "Follow-up Email", "InMail", "Referral Call"], variable=self.type_var, width=420).pack(pady=(5, 15))
        
        ctk.CTkLabel(self, text="Contact / Recruiter Name", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=40)
        self.contact_entry = ctk.CTkEntry(self, placeholder_text="Name of the person you contacted...", height=35, width=420)
        self.contact_entry.pack(pady=(5, 15))
        
        ctk.CTkLabel(self, text="Tactical Message Snippet", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=40)
        self.msg_text = ctk.CTkTextbox(self, height=120, width=420)
        self.msg_text.pack(pady=(5, 15))
        
        ctk.CTkButton(self, text="💾 RECORD OUTREACH ACTIVITY", height=50, width=300, fg_color="#27ae60", command=self.save).pack(pady=20)
        
    def save(self):
        o_type = self.type_var.get()
        name = self.contact_entry.get().strip()
        msg = self.msg_text.get("1.0", "end").strip()
        
        # Tactical Database Recording (v32.9)
        if hasattr(self.parent, 'tracker'):
            self.parent.tracker.add_outreach_log(self.job['id'], o_type, name, msg)
            print(f"✓ Strategic Outreach Recorded: {o_type} to {name}")
        
        self.destroy()

class HelpCenterWindow(ctk.CTkToplevel):
    """Sovereign Help Center: Professional 'App Password' Masterclass."""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Sovereign Agent | Help Center")
        self.geometry("700x750")
        self.transient(parent)
        self.grab_set()
        
        # Navigation / Tabs
        tabs = ctk.CTkTabview(self, fg_color="transparent")
        tabs.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.tab_gmail = tabs.add("📧 GMAIL")
        self.tab_yahoo = tabs.add("🟣 YAHOO / AOL")
        self.tab_outlook = tabs.add("🔵 OUTLOOK")
        self.tab_security = tabs.add("🛡️ SECURITY")
        self.tab_dash = tabs.add("📊 DASHBOARD")
        
        self._build_gmail_tab()
        self._build_yahoo_tab()
        self._build_outlook_tab()
        self._build_security_tab()
        self._build_dashboard_tab()

    def _build_dashboard_tab(self):
        t = self.tab_dash
        ctk.CTkLabel(t, text="MISSION CONTROL TELEMETRY GUIDE", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00d4ff").pack(pady=15)
        guide = (
            "● DEPLOYED APPS: Total successful applications recorded in mission logs.\n"
            "● INTERVIEW LEADS: High-value targets currently in interview phase.\n"
            "● INTEL TARGETS: All discovered job opportunities across all platforms.\n"
            "● EFFICIENCY RATE: Your strike-to-target ratio (Applications / Discoveries).\n"
            "● PROGRESS FUNNEL: Visual pipeline of your current campaign status.\n"
            "● PLATFORM DENSITY: Intelligence on which sources are yielding the most hits.\n"
            "● REAL-TIME TELEMETRY: Live low-level logs from active automation engines."
        )
        ctk.CTkLabel(t, text=guide, justify="left", font=("Inter", 12)).pack(padx=30, pady=10)

    def _build_gmail_tab(self):
        t = self.tab_gmail
        ctk.CTkLabel(t, text="GOOGLE APP PASSWORD GUIDE", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2ecc71").pack(pady=15)
        guide = (
            "1. Enable 2-Step Verification in your Google Account Security tab.\n"
            "2. Navigate to 'Security' -> '2-Step Verification'.\n"
            "3. Scroll to the absolute bottom and click 'App passwords'.\n"
            "4. Enter 'Sovereign Agent' for the App name and click Create.\n"
            "5. Copy the 16-character code into the Agent's Password field."
        )
        ctk.CTkLabel(t, text=guide, justify="left", font=("Inter", 12)).pack(padx=30, pady=10)
        ctk.CTkButton(t, text="🔗 OPEN GOOGLE SECURITY CENTER", fg_color="#34495e", 
                      command=lambda: webbrowser.open("https://myaccount.google.com/security")).pack(pady=20)

    def _build_yahoo_tab(self):
        t = self.tab_yahoo
        ctk.CTkLabel(t, text="YAHOO / AOL APP PASSWORD GUIDE", font=ctk.CTkFont(size=16, weight="bold"), text_color="#8e44ad").pack(pady=15)
        guide = (
            "1. Log in to Yahoo and go to 'Account Info'.\n"
            "2. Click 'Account Security' in the sidebar.\n"
            "3. Scroll to 'Generate App Password' at the bottom.\n"
            "4. Select 'Other App' and type 'Sovereign Agent'.\n"
            "5. Copy the generated code and use it in the Dashboard."
        )
        ctk.CTkLabel(t, text=guide, justify="left", font=("Inter", 12)).pack(padx=30, pady=10)
        ctk.CTkButton(t, text="🔗 OPEN YAHOO SECURITY", fg_color="#34495e", 
                      command=lambda: webbrowser.open("https://login.yahoo.com/account/security")).pack(pady=20)

    def _build_outlook_tab(self):
        t = self.tab_outlook
        ctk.CTkLabel(t, text="OUTLOOK / OFFICE 365 GUIDE", font=ctk.CTkFont(size=16, weight="bold"), text_color="#2980b9").pack(pady=15)
        guide = (
            "1. Go to Microsoft 'Account Dashboard' and select 'Security'.\n"
            "2. Click on 'Advanced Security Options'.\n"
            "3. Ensure 'Two-step verification' is turned ON.\n"
            "4. Look for the 'App Passwords' section and click 'Create a new app password'.\n"
            "5. Note the code and enter it into the Agent's settings."
        )
        ctk.CTkLabel(t, text=guide, justify="left", font=("Inter", 12)).pack(padx=30, pady=10)
        ctk.CTkButton(t, text="🔗 OPEN MICROSOFT SECURITY", fg_color="#34495e", 
                      command=lambda: webbrowser.open("https://account.microsoft.com/security")).pack(pady=20)

    def _build_security_tab(self):
        t = self.tab_security
        ctk.CTkLabel(t, text="MISSION SECURITY PROTOCOLS", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00d4ff").pack(pady=15)
        guide = (
            "● ZERO-CLOUD: All your data is stored locally in your %APPDATA% directory.\n"
            "● NO TELEMETRY: We do not track your applications or personal data.\n"
            "● ENCRYPTED KEYS: Your API keys are never saved in plain text in any logs.\n"
            "● SECURE HEADLESS: Browser sessions are isolated to prevent cross-site tracking.\n"
            "● YOU OWN THE IDENTITY: You can delete the entire database with one click."
        )
        ctk.CTkLabel(t, text=guide, justify="left", font=("Inter", 12)).pack(padx=30, pady=10)
        
        # Phase 35.0: Update Section
        ctk.CTkFrame(t, height=2, fg_color="#333").pack(fill="x", pady=20, padx=30)
        
        ctk.CTkLabel(t, text=f"SOVEREIGN AGENT v{config.VERSION}", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray").pack()
        
        update_btn = ctk.CTkButton(t, text="🔍 CHECK FOR UPDATES", height=40, width=200, fg_color="#34495e", command=self.manual_check)
        update_btn.pack(pady=10)
        
        self.status_lbl = ctk.CTkLabel(t, text="", font=ctk.CTkFont(size=10))
        self.status_lbl.pack()

    def manual_check(self):
        self.status_lbl.configure(text="Connecting to GitHub HQ...", text_color="gray")
        def run():
            from src.update_manager import check_for_updates, get_update_info
            if check_for_updates():
                info = get_update_info()
                ver = info.get('version', 'latest')
                self.status_lbl.configure(
                    text=f"⚡ v{ver} AVAILABLE — Close this window and click the update banner", 
                    text_color="#f1c40f"
                )
                if hasattr(self.master, '_signal_update_available'):
                    self.master.after(0, lambda: self.master._signal_update_available(info))
            else:
                self.status_lbl.configure(text="✓ YOUR AGENT IS UP TO DATE", text_color="#2ecc71")
        
        threading.Thread(target=run, daemon=True).start()


class EmailScanDialog(ctk.CTkToplevel):
    """Platform Selection for Email Intelligence Scan."""
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.title("Email Intelligence Filter")
        self.geometry("400x350")
        self.transient(parent)
        self.grab_set()
        self.callback = callback
        
        ctk.CTkLabel(self, text="SELECT SOURCES TO SCAN", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00d4ff").pack(pady=20)
        
        self.plat_vars = {}
        platforms = ["LinkedIn", "Indeed", "Glassdoor", "ZipRecruiter", "Monster", "CareerBuilder"]
        for plat in platforms:
            var = ctk.BooleanVar(value=True if plat in ["LinkedIn", "Indeed"] else False)
            cb = ctk.CTkCheckBox(self, text=plat, variable=var)
            cb.pack(pady=5, padx=50, anchor="w")
            self.plat_vars[plat] = var
            
        ctk.CTkButton(self, text="🔍 START SCAN", fg_color="#2980b9", command=self.confirm).pack(pady=25)

    def confirm(self):
        selected = [p for p, v in self.plat_vars.items() if v.get()]
        self.callback(selected)
        self.destroy()

if __name__ == "__main__":
    app = JobAutomationApp()
    app.update_idletasks() # Anti-crash measure for ctk titlebar on Python 3.13/Windows
    app.mainloop()
