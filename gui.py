import os
import sys
import threading
import time
import shutil
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from datetime import datetime

import customtkinter as ctk
from PIL import Image, ImageTk
from dotenv import set_key

import config
from src.applicant_profile import ApplicantProfile
from src.tracker import Tracker
from src.applicant_bot import get_bot

# Set appearance and theme
ctk.set_appearance_mode(config.GUI_APPEARANCE_MODE)
ctk.set_default_color_theme(config.GUI_COLOR_THEME)

# --- Theme Configuration ---
ACCENT_COLOR = config.GUI_ACCENT_COLOR
BG_COLOR = "#0d1117"
CARD_COLOR = "#161b22"
BORDER_COLOR = "#30363d"
TEXT_PRIMARY = "#c9d1d9"
TEXT_SECONDARY = "#8b949e"

class LogRedirector:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, str):
        if not self.textbox.winfo_exists(): return
        self.textbox.configure(state="normal")
        self.textbox.insert("end", str)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def flush(self):
        pass

class JobAutomationApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self._initializing = True
        self.title(f"Sovereign Agent v{open('VERSION').read().strip()} | TDWAS Technology")
        self.geometry("1280x800")
        
        # Load profile and tracker
        self.profile = ApplicantProfile()
        self.tracker = Tracker()
        
        # UI State
        self._current_frame_name = "Dashboard"
        self._old_stdout = sys.stdout
        
        # Theme handling
        self.configure(fg_color=BG_COLOR)
        
        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        self.setup_sidebar()
        self.setup_frames()
        self.select_frame_by_name("Dashboard")
        
        # Redirect stdout to console box
        self.enable_redirection()
        
        # Initial stats refresh
        self.after(1000, self.refresh_stats)
        self.after(2000, self.refresh_stats_loop)
        
        self.check_onboarding()
        self._initializing = False

    def setup_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        # Header / Brand
        brand_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand_frame.pack(pady=30, padx=20, fill="x")
        
        try:
            logo_img = Image.open("image/favicon.ico").resize((32, 32))
            self.logo_photo = ImageTk.PhotoImage(logo_img)
            ctk.CTkLabel(brand_frame, image=self.logo_photo, text="").pack(side="left")
        except: pass
        
        ctk.CTkLabel(brand_frame, text="SOVEREIGN", font=ctk.CTkFont(size=20, weight="bold"), text_color=ACCENT_COLOR).pack(side="left", padx=10)
        
        # Navigation
        self.nav_btns = {}
        nav_items = [
            ("Dashboard", "📊"),
            ("CRM", "👥"),
            ("System Core", "⚙️"),
            ("Intelligence", "🧠")
        ]
        
        for name, icon in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=f"{icon}  {name}", 
                height=45, corner_radius=8, 
                fg_color="transparent", text_color=TEXT_PRIMARY,
                anchor="w", font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda n=name: self.select_frame_by_name(n)
            )
            btn.pack(pady=4, padx=15, fill="x")
            self.nav_btns[name] = btn

    def setup_frames(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        
        # 1. DASHBOARD FRAME
        self.dashboard_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_dashboard()
        
        # 2. CRM FRAME
        self.crm_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_crm()
        
        # 3. SYSTEM CORE FRAME
        self.core_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_core()
        
        # 4. INTELLIGENCE FRAME
        self.intel_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_intelligence()

    def setup_dashboard(self):
        # Stats Cards
        stats_container = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        stats_container.pack(fill="x", pady=(0, 20))
        
        self.stat_cards = {}
        for i, (label, color) in enumerate([("JOBS FOUND", "#3498db"), ("APPLIED", "#2ecc71"), ("INTERVIEWS", "#9b59b6"), ("OFFERS", "#f1c40f")]):
            card = ctk.CTkFrame(stats_container, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
            card.pack(side="left", fill="both", expand=True, padx=5)
            
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=(15, 0))
            val = ctk.CTkLabel(card, text="0", font=ctk.CTkFont(size=28, weight="bold"), text_color=color)
            val.pack(pady=(0, 15))
            self.stat_cards[label] = val

        # Main Area
        main_area = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        main_area.pack(fill="both", expand=True)
        
        # Readiness Checklist (Left)
        checklist = ctk.CTkFrame(main_area, width=300, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
        checklist.pack(side="left", fill="y", padx=(0, 10))
        
        ctk.CTkLabel(checklist, text="MISSION READINESS", font=ctk.CTkFont(size=14, weight="bold"), text_color=ACCENT_COLOR).pack(pady=20)
        
        self.ready_ai = ctk.CTkLabel(checklist, text="○ AI Synapse", text_color="gray", font=ctk.CTkFont(size=13))
        self.ready_ai.pack(pady=10, padx=20, anchor="w")
        self.ready_id = ctk.CTkLabel(checklist, text="○ Identity Sync", text_color="gray", font=ctk.CTkFont(size=13))
        self.ready_id.pack(pady=10, padx=20, anchor="w")
        self.ready_resume = ctk.CTkLabel(checklist, text="○ Master Resume", text_color="gray", font=ctk.CTkFont(size=13))
        self.ready_resume.pack(pady=10, padx=20, anchor="w")
        
        # Quick Actions
        ctk.CTkButton(checklist, text="⚡ LAUNCH FULL PIPELINE", height=45, fg_color="#2ecc71", hover_color="#27ae60", font=ctk.CTkFont(weight="bold"), command=self.run_full_pipeline).pack(pady=30, padx=20, fill="x")
        ctk.CTkButton(checklist, text="🔍 SURGICAL STRIKE", height=40, fg_color="#3498db", command=lambda: self.select_frame_by_name("Intelligence")).pack(pady=5, padx=20, fill="x")

        # Console Output (Right)
        console_frame = ctk.CTkFrame(main_area, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
        console_frame.pack(side="right", fill="both", expand=True)
        
        ctk.CTkLabel(console_frame, text="SOVEREIGN CONSOLE", font=ctk.CTkFont(size=12, weight="bold"), text_color=TEXT_SECONDARY).pack(pady=10, padx=20, anchor="w")
        self.log_box = ctk.CTkTextbox(console_frame, fg_color="#0d1117", text_color="#00d4ff", font=("Consolas", 12), border_color="#1f2937", border_width=1)
        self.log_box.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.log_box.configure(state="disabled")

    def setup_crm(self):
        header = ctk.CTkFrame(self.crm_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        ctk.CTkLabel(header, text="MISSION TARGETS (CRM)", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        ctk.CTkButton(header, text="🔄 REFRESH FEED", width=120, command=self.refresh_crm_feed).pack(side="right", padx=10)
        
        # Search Bar
        self.crm_search = ctk.CTkEntry(self.crm_frame, placeholder_text="Filter targets by company or title...", height=40)
        self.crm_search.pack(fill="x", pady=(0, 15))
        
        # Scrollable Feed
        self.feed_scroll = ctk.CTkScrollableFrame(self.crm_frame, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
        self.feed_scroll.pack(fill="both", expand=True)

    def setup_core(self):
        sc = ctk.CTkScrollableFrame(self.core_frame, fg_color="transparent")
        sc.pack(fill="both", expand=True)
        
        # 1. AI IDENTITY BRAIN
        ai_brain = ctk.CTkFrame(sc, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
        ai_brain.pack(fill="x", pady=10)
        ctk.CTkLabel(ai_brain, text="AI INTELLIGENCE BRAIN", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT_COLOR).pack(pady=15, padx=20, anchor="w")
        
        self.provider_var = ctk.StringVar(value=config.LLM_PROVIDER)
        self.provider_box = ctk.CTkOptionMenu(ai_brain, values=["openai", "gemini", "claude", "ollama", "lmstudio", "groq", "openrouter"], variable=self.provider_var, command=self.update_provider_visibility)
        self.provider_box.pack(pady=10, padx=20, anchor="w")
        
        self.token_label = ctk.CTkLabel(ai_brain, text="API Key / Endpoint:", text_color=TEXT_SECONDARY)
        self.token_label.pack(padx=20, anchor="w")
        self.key_entry = ctk.CTkEntry(ai_brain, show="*", width=500, height=35)
        self.key_entry.pack(pady=5, padx=20, anchor="w")
        
        # Store current keys in dict for switching
        self.provider_keys = {
            "openai": config.OPENAI_API_KEY,
            "gemini": config.GEMINI_API_KEY,
            "claude": config.ANTHROPIC_API_KEY,
            "ollama": config.OLLAMA_BASE_URL,
            "lmstudio": config.LMSTUDIO_BASE_URL,
            "groq": _get("GROQ_API_KEY"),
            "openrouter": config.OPENROUTER_API_KEY
        }
        self.key_entry.insert(0, self.provider_keys.get(config.LLM_PROVIDER, ""))
        
        # Model Selection
        ctk.CTkLabel(ai_brain, text="Active Model:", text_color=TEXT_SECONDARY).pack(padx=20, anchor="w")
        self.model_var = ctk.StringVar(value=self._get_current_model())
        self.provider_models = {
            "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            "gemini": ["gemini-1.5-pro", "gemini-1.5-flash"],
            "claude": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"],
            "ollama": ["llama3", "mistral", "phi3"],
            "lmstudio": ["local-model"],
            "groq": ["llama-3.1-70b-versatile", "mixtral-8x7b-32768"],
            "openrouter": ["google/gemini-2.0-flash-001", "anthropic/claude-3.5-sonnet"]
        }
        self.model_box = ctk.CTkOptionMenu(ai_brain, values=self.provider_models.get(config.LLM_PROVIDER, ["default"]), variable=self.model_var, command=self.save_model_choice)
        self.model_box.pack(pady=10, padx=20, anchor="w")
        
        ctk.CTkButton(ai_brain, text="SAVE BRAIN CONFIG", command=self.save_provider_key).pack(pady=20, padx=20, anchor="e")

        # 2. PLATFORM CREDENTIALS
        plat_cred = ctk.CTkFrame(sc, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
        plat_cred.pack(fill="x", pady=10)
        ctk.CTkLabel(plat_cred, text="PLATFORM CREDENTIALS", font=ctk.CTkFont(size=16, weight="bold"), text_color=ACCENT_COLOR).pack(pady=15, padx=20, anchor="w")
        
        # We'll use a grid for credentials
        grid = ctk.CTkFrame(plat_cred, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=10)
        
        # LinkedIn
        ctk.CTkLabel(grid, text="LinkedIn Email:").grid(row=0, column=0, sticky="w", pady=5)
        self.li_email = ctk.CTkEntry(grid, width=250)
        self.li_email.grid(row=0, column=1, padx=10, pady=5)
        self.li_email.insert(0, config.LINKEDIN_EMAIL or "")
        
        ctk.CTkLabel(grid, text="LinkedIn Password:").grid(row=1, column=0, sticky="w", pady=5)
        self.li_pass = ctk.CTkEntry(grid, show="*", width=250)
        self.li_pass.grid(row=1, column=1, padx=10, pady=5)
        self.li_pass.insert(0, config.LINKEDIN_PASSWORD or "")
        
        # Indeed
        ctk.CTkLabel(grid, text="Indeed Email:").grid(row=0, column=2, sticky="w", pady=5, padx=(30, 0))
        self.in_email = ctk.CTkEntry(grid, width=250)
        self.in_email.grid(row=0, column=3, padx=10, pady=5)
        self.in_email.insert(0, config.INDEED_EMAIL or "")
        
        ctk.CTkLabel(grid, text="Indeed Password:").grid(row=1, column=2, sticky="w", pady=5, padx=(30, 0))
        self.in_pass = ctk.CTkEntry(grid, show="*", width=250)
        self.in_pass.grid(row=1, column=3, padx=10, pady=5)
        self.in_pass.insert(0, config.INDEED_PASSWORD or "")
        
        ctk.CTkButton(plat_cred, text="SAVE MISSION STRATEGY", command=self.save_mission_strategy).pack(pady=20, padx=20, anchor="e")

    def setup_intelligence(self):
        # Surgical Strike Area
        surgical = ctk.CTkFrame(self.intel_frame, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
        surgical.pack(fill="x", pady=10)
        ctk.CTkLabel(surgical, text="SURGICAL STRIKE (DIRECT APPLY)", font=ctk.CTkFont(size=18, weight="bold"), text_color=ACCENT_COLOR).pack(pady=15, padx=20, anchor="w")
        
        self.surgical_url_entry = ctk.CTkEntry(surgical, placeholder_text="Paste Job URL (LinkedIn, Indeed, Greenhouse, etc.)", height=45)
        self.surgical_url_entry.pack(fill="x", padx=20, pady=10)
        
        opt_frame = ctk.CTkFrame(surgical, fg_color="transparent")
        opt_frame.pack(fill="x", padx=20, pady=10)
        
        self.guided_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(opt_frame, text="Guided Mode (Manual Question Review)", variable=self.guided_var).pack(side="left", padx=10)
        
        self.strike_plat_var = ctk.StringVar(value="Auto-Detect")
        ctk.CTkOptionMenu(opt_frame, values=["Auto-Detect", "LinkedIn", "Indeed", "Greenhouse", "Lever"], variable=self.strike_plat_var).pack(side="left", padx=20)
        
        ctk.CTkButton(surgical, text="🚀 EXECUTE SURGICAL APPLY", height=45, width=250, fg_color="#e67e22", hover_color="#d35400", font=ctk.CTkFont(weight="bold"), command=self.run_surgical_apply).pack(side="right", padx=20, pady=20)
        ctk.CTkButton(surgical, text="📄 GEN ASSETS ONLY", height=45, width=150, fg_color="#34495e", command=lambda: self.run_surgical_apply(only_docs=True)).pack(side="right", padx=10, pady=20)

        # Email Discovery Scan
        email_scan = ctk.CTkFrame(self.intel_frame, fg_color=CARD_COLOR, border_color=BORDER_COLOR, border_width=1, corner_radius=12)
        email_scan.pack(fill="x", pady=10)
        ctk.CTkLabel(email_scan, text="INTELLIGENCE CORE (EMAIL DISCOVERY)", font=ctk.CTkFont(size=18, weight="bold"), text_color=ACCENT_COLOR).pack(pady=15, padx=20, anchor="w")
        
        ctk.CTkLabel(email_scan, text="Deep discovery engine scans your inbox folders for hidden job alerts and auto-filters based on mission profile.", text_color=TEXT_SECONDARY, wraplength=800).pack(padx=20, anchor="w")
        
        btn_frame = ctk.CTkFrame(email_scan, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(btn_frame, text="🔍 SCAN INBOX NOW", height=45, width=200, fg_color="#2ecc71", command=self.run_email_scan).pack(side="left")
        ctk.CTkButton(btn_frame, text="⚙️ CONFIG DISCOVERY", height=45, width=180, fg_color="#34495e", command=self._show_help_center).pack(side="left", padx=15)
        ctk.CTkButton(btn_frame, text="📡 TEST CONNECTION", height=45, width=180, fg_color="#34495e", command=self.test_email_discovery).pack(side="left")

    def select_frame_by_name(self, name):
        # Update Nav UI
        for n, btn in self.nav_btns.items():
            btn.configure(fg_color="#3b82f6" if n == name else "transparent", text_color="white" if n == name else TEXT_PRIMARY)
        
        # Show/Hide Frames
        self.dashboard_frame.pack_forget()
        self.crm_frame.pack_forget()
        self.core_frame.pack_forget()
        self.intel_frame.pack_forget()
        
        if name == "Dashboard": self.dashboard_frame.pack(fill="both", expand=True)
        elif name == "CRM": 
            self.crm_frame.pack(fill="both", expand=True)
            self.refresh_crm_feed()
        elif name == "System Core": self.core_frame.pack(fill="both", expand=True)
        elif name == "Intelligence": self.intel_frame.pack(fill="both", expand=True)
        
        self._current_frame_name = name

    def refresh_stats(self):
        stats = self.tracker.get_stats()
        self.stat_cards["JOBS FOUND"].configure(text=str(stats.get('total', 0)))
        self.stat_cards["APPLIED"].configure(text=str(stats.get('applied', 0)))
        self.stat_cards["INTERVIEWS"].configure(text=str(stats.get('interviewing', 0)))
        self.stat_cards["OFFERS"].configure(text=str(stats.get('offers', 0)))
        self.update_readiness_ui()

    def refresh_crm_feed(self):
        if not self.winfo_exists() or self._current_frame_name != "CRM": return
        for w in self.feed_scroll.winfo_children(): w.destroy()
        
        jobs = self.tracker.get_pending_reviews()
        if not jobs:
            ctk.CTkLabel(self.feed_scroll, text="No active mission targets detected.", text_color="gray").pack(pady=40)
        else:
            for job in jobs[:50]:
                self._create_job_row(self.feed_scroll, job)

    def _create_job_row(self, parent, job):
        row = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=10)
        row.pack(fill="x", pady=4, padx=5)
        
        content = ctk.CTkFrame(row, fg_color="transparent")
        content.pack(side="left", fill="both", expand=True, padx=15, pady=10)
        
        ctk.CTkLabel(content, text=job['job_title'], font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(content, text=f"{job['company']} • {job['location']} • {job['source']}", font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w")
        
        reason = job.get('match_reason') or ""
        if reason:
            ctk.CTkLabel(content, text=f"🤖 {reason}", font=ctk.CTkFont(size=10, slant="italic"), text_color="#2ecc71").pack(anchor="w", pady=(2, 0))
            
        score_color = "#2ecc71" if job.get('match_score', 0) > 80 else "#f1c40f" if job.get('match_score', 0) > 60 else "#e67e22"
        ctk.CTkLabel(row, text=f"{job.get('match_score', 0)}%", text_color=score_color, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=20)
        
        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(side="right", padx=10)
        
        ctk.CTkButton(actions, text="APPLY", width=70, height=28, fg_color="#2980b9", command=lambda j=job: self._quick_apply_logic(j)).pack(side="left", padx=5)
        ctk.CTkButton(actions, text="✅", width=35, height=28, fg_color="#27ae60", command=lambda j=job: self._mark_applied_logic(j)).pack(side="left", padx=5)
        ctk.CTkButton(actions, text="🗑️", width=35, height=28, fg_color="#c0392b", command=lambda j=job: self._delete_job_logic(j)).pack(side="left", padx=5)

    def refresh_stats_loop(self):
        if not self.winfo_exists(): return
        try:
            if self._current_frame_name == "Dashboard":
                self.refresh_stats()
        except: pass
        self.after(5000, self.refresh_stats_loop)

    def run_surgical_apply(self, only_docs=False):
        url = self.surgical_url_entry.get().strip()
        if not url:
            messagebox.showwarning("Target Required", "Please enter a valid job URL.")
            return
        
        def run_strike():
            try:
                from src.applicant_bot import apply_to_job
                # simplified for brevity
                print(f"[Operation] Initiating surgical strike on: {url}")
                # logic...
            except Exception as e:
                print(f"[Error] Surgical strike failed: {e}")
                
        self._run_in_thread(run_strike, name="Surgical Apply")
        self.select_frame_by_name("Dashboard")

    def run_full_pipeline(self):
        ai_ok, id_ok, res_ok = self.get_mission_status()
        if not (ai_ok and id_ok and res_ok):
            print("\n[Security] ✗ MISSION ABORTED: Readiness Checklist Incomplete.")
            return

        config.reload_from_env()
        print("[Operation] INITIATING FULL AUTO-PIPELINE...")
        
        def run_pipe():
            from main import run_auto_pipeline
            run_auto_pipeline(days_back=float(config.DAYS_BACK))
            self.after(0, self.refresh_stats)
            
        self._run_in_thread(run_pipe, name="Full Pipeline")
        self.select_frame_by_name("Dashboard")

    def test_email_discovery(self):
        print(f"[System] Initiating Intelligence Core handshake...")
        def run_test():
            from src.email_scanner import EmailScanner
            try:
                scanner = EmailScanner()
                if scanner.test_connection():
                    print("[System] ✓ Intelligence Core Online.")
                else:
                    print("[System] ✗ Intelligence Core Offline.")
            except Exception as e:
                print(f"[Error] Handshake failed: {e}")
        self._run_in_thread(run_test, name="Email Sync Test")

    def run_email_scan(self):
        def run_scan():
            from src.email_scanner import EmailScanner
            scanner = EmailScanner()
            alerts = scanner.scan(days_back=float(config.DAYS_BACK))
            print(f"[Intelligence] Identified {len(alerts)} valid targets.")
            # Sync to tracker...
            self.after(0, self.refresh_stats)
        self._run_in_thread(run_scan, name="Email Scan")

    def save_mission_strategy(self):
        """Wrapper for saving mission-critical configuration."""
        self.save_platform_credentials()

    def save_platform_credentials(self):
        if self._initializing: return
        set_key(str(ENV_PATH), "LINKEDIN_EMAIL", self.li_email.get())
        set_key(str(ENV_PATH), "LINKEDIN_PASSWORD", self.li_pass.get())
        set_key(str(ENV_PATH), "INDEED_EMAIL", self.in_email.get())
        set_key(str(ENV_PATH), "INDEED_PASSWORD", self.in_pass.get())
        config.reload_from_env()
        print("[System] Platform credentials synchronized.")

    def update_provider_visibility(self, provider):
        # Update UI for provider brain switching
        pass

    def save_model_choice(self, model):
        pass

    def save_provider_key(self):
        pass

    def enable_redirection(self):
        if hasattr(self, 'log_box'):
            sys.stdout = LogRedirector(self.log_box)

    def get_mission_status(self):
        ai_key = self.provider_keys.get(config.LLM_PROVIDER, "")
        ai_ready = len(str(ai_key)) > 5
        id_ready = True # Simplified
        res_ready = config.BASE_RESUME_PDF.exists() or config.BASE_RESUME_DOCX.exists()
        return ai_ready, id_ready, res_ready

    def update_readiness_ui(self):
        ai, ident, res = self.get_mission_status()
        self.ready_ai.configure(text=f"{'✅' if ai else '○'} AI Synapse", text_color="#2ecc71" if ai else "gray")
        self.ready_id.configure(text=f"{'✅' if ident else '○'} Identity Sync", text_color="#2ecc71" if ident else "gray")
        self.ready_resume.configure(text=f"{'✅' if res else '○'} Master Resume", text_color="#2ecc71" if res else "gray")

    def check_onboarding(self):
        self.update_readiness_ui()

    def _run_in_thread(self, func, name="Task"):
        t = threading.Thread(target=func, name=name, daemon=True)
        t.start()

    def _get_current_model(self):
        return "default"

    def _quick_apply_logic(self, job):
        self.surgical_url_entry.delete(0, "end")
        self.surgical_url_entry.insert(0, job['apply_url'])
        self.run_surgical_apply()

    def _mark_applied_logic(self, job):
        self.tracker.update_status(job['id'], 'applied')
        self.refresh_crm_feed()
        self.refresh_stats()

    def _delete_job_logic(self, job):
        if messagebox.askyesno("Confirm", f"Delete {job['job_title']}?"):
            self.tracker.delete(job['id'])
            self.refresh_crm_feed()
            self.refresh_stats()

    def _show_help_center(self): pass

if __name__ == "__main__":
    app = JobAutomationApp()
    app.mainloop()
