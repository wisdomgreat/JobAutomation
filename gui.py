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
        self.db_path = Path(resource_path("data/applications.db"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.tracker = Tracker(self.db_path)

        # Window Setup
        self.title("JobBot Sovereign Agent v25.0")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        # Phase 24: Store original stdout to restore on close
        self._old_stdout = sys.stdout
        self.protocol("WM_DELETE_WINDOW", self.on_closing)


        # Phase 32: Legal Compliance
        self.legal_var = ctk.BooleanVar(value=False)
        
        # ─── Layout ───
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ─── Navigation Sidebar ───
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1) # Spacer

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SOVEREIGN AGENT", font=ctk.CTkFont(size=22, weight="bold"))

        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Nav Buttons (Sovereign Executive Style)
        self.dashboard_btn = self._create_nav_btn("🏠 DASHBOARD", 1, self.show_dashboard)
        self.search_btn = self._create_nav_btn("🔍 TARGET SCAN", 2, self.show_search)
        self.assets_btn = self._create_nav_btn("📋 ASSET HUB", 3, self.show_assets)
        self.analytics_btn = self._create_nav_btn("📈 INTELLIGENCE", 4, self.show_analytics)
        self.settings_btn = self._create_nav_btn("⚙️ SYSTEM CORE", 5, self.show_settings)
        self.support_btn = self._create_nav_btn("🤝 HELP & SUPPORT", 6, self.show_support)

        # Live Status Card in Sidebar
        self.status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#1a1a1a", corner_radius=10)
        self.status_frame.grid(row=11, column=0, padx=20, pady=20, sticky="ew")
        self.status_title = ctk.CTkLabel(self.status_frame, text="SYSTEM STATUS", font=ctk.CTkFont(size=10, weight="bold"))
        self.status_title.pack(pady=(10, 0))
        self.status_indic = ctk.CTkLabel(self.status_frame, text="● READY", text_color="#2ecc71", font=ctk.CTkFont(weight="bold"))
        self.status_indic.pack(pady=(0, 10))

        # ─── Main Content Area ───
        
        # 1. Dashboard Frame
        self.dashboard_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.dashboard_frame.grid_columnconfigure(0, weight=4) # Feed
        self.dashboard_frame.grid_columnconfigure(1, weight=3) # Terminal
        self._build_dashboard_ui()

        # SMART ONBOARDING: If no keys, show settings first
        if not _get("OPENROUTER_API_KEY") and not _get("OPENAI_API_KEY"):
            self.after(1000, lambda: self._show_onboarding_alert())
            self.after(1500, lambda: self.select_frame_by_name("Settings"))

    def _show_onboarding_alert(self):
        print("\n" + "═"*50)
        print(" 🚀 WELCOME TO SOVEREIGN AGENT")
        print("" + "═"*50)
        print(" [SYSTEM] First-run detected. Please configure your")
        print(" [SYSTEM] API Keys in the 'SYSTEM CORE' tab to begin.")
        print("═"*50 + "\n")

        # 2. Search Tab Frame
        self.search_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.search_frame.grid_columnconfigure(0, weight=1)
        self._build_search_ui()

        # 3. Assets Frame (Resume Manager)
        self.assets_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.assets_frame.grid_columnconfigure(0, weight=1)
        self._build_assets_ui()

        # 4. Analytics Frame
        self.analytics_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.analytics_frame.grid_columnconfigure(0, weight=1)
        self._build_analytics_ui()

        # 5. Settings Frame
        self.settings_frame = ctk.CTkScrollableFrame(self, corner_radius=0, fg_color="transparent")
        self.settings_frame.grid_columnconfigure(0, weight=1)
        self._build_settings_ui()

        # 6. Support Frame
        self.support_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.support_frame.grid_columnconfigure(0, weight=1)
        self._build_support_ui()

        self.select_frame_by_name("Dashboard")
        self.refresh_stats()

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

        # Buttons
        self.run_btn = ctk.CTkButton(left_panel, text="⚡ LAUNCH AUTO-PIPELINE", fg_color="#2ecc71", hover_color="#27ae60", height=60, font=ctk.CTkFont(size=16, weight="bold"), command=self.run_pipeline)
        self.run_btn.grid(row=2, column=0, sticky="ew", pady=10)
        self.run_btn.configure(state="disabled") # Locked until legal check

        # Job Feed
        self.feed_frame = ctk.CTkScrollableFrame(left_panel, label_text="RECENT MISSIONS", label_font=ctk.CTkFont(weight="bold"), height=400)
        self.feed_frame.grid(row=3, column=0, sticky="nsew", pady=10)

        # RIGHT: Live Terminal
        right_panel = ctk.CTkFrame(self.dashboard_frame, fg_color="#0d0d0d", corner_radius=15, border_width=1, border_color="#333")
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 20), pady=40)
        right_panel.grid_rowconfigure(1, weight=1)
        right_panel.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(right_panel, text="LIVE OPERATIONS CONSOLE", font=ctk.CTkFont(size=12, weight="bold", family="Consolas"), text_color="#2ecc71").grid(row=0, column=0, pady=10)
        self.log_box = ctk.CTkTextbox(right_panel, fg_color="transparent", font=ctk.CTkFont(family="Consolas", size=11), text_color="#2ecc71", wrap="word")
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        sys.stdout = LogRedirector(self.log_box)

    def _build_assets_ui(self):
        ctk.CTkLabel(self.assets_frame, text="Asset Manager (A/B Testing)", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=(30, 10), sticky="w")
        ctk.CTkLabel(self.assets_frame, text="Manage multiple resumes and auto-detect target roles for maximum success.", text_color="gray").grid(row=1, column=0, padx=30, pady=(0, 20), sticky="w")
        
        # Resume Table (Actual Files from Output)
        self.asset_scroll = ctk.CTkScrollableFrame(self.assets_frame, height=500)
        self.asset_scroll.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        self.refresh_assets_list()

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
                
                # Look for PDF
                pdfs = list(sub.glob("Resume*.pdf"))
                if pdfs:
                    ctk.CTkButton(row, text="VIEW PDF", width=100, height=28, fg_color="#27ae60",
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

        self.search_btn_main = ctk.CTkButton(self.search_frame, text="🛰️ INITIATE SCAN", height=60, font=ctk.CTkFont(weight="bold"), command=self.run_semi_auto_search)
        self.search_btn_main.grid(row=3, column=0, padx=30, pady=10, sticky="ew")
        self.search_btn_main.configure(state="disabled") # Locked until legal check

        # Phase 27.0: Tactical Controls
        tactical_frame = ctk.CTkFrame(self.search_frame, fg_color="#1a1a1a", corner_radius=15, border_width=1, border_color="#333")
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
        
        # Stealth Toggle
        self.stealth_var = ctk.BooleanVar(value=True)
        self.stealth_toggle = ctk.CTkSwitch(tactical_frame, text="BEHAVIORAL STEALTH (Human Mimicry)", variable=self.stealth_var, progress_color="#2ecc71")
        self.stealth_toggle.pack(pady=10)

    def update_match_label(self, val):
        config.MATCH_SCORE_THRESHOLD = int(val)
        self.match_label.configure(text=f"Match Intensity: {int(val)}%")

    def _create_form_row(self, parent, label, dummy, row):
        ctk.CTkLabel(parent, text=label, width=150, anchor="w").grid(row=row, column=0, padx=20, pady=15)
        entry = ctk.CTkEntry(parent, placeholder_text=dummy, height=40)
        entry.grid(row=row, column=1, padx=20, pady=15, sticky="ew")
        return entry

    def _build_settings_ui(self):
        ctk.CTkLabel(self.settings_frame, text="Core Configuration", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        
        # Combined Settings view
        self.env_entries = {}
        keys = ["LLM_PROVIDER", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "GEMINI_API_KEY", "LINKEDIN_EMAIL", "YAHOO_EMAIL"]
        for i, key in enumerate(keys):
            frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
            frame.grid(row=i+1, column=0, padx=30, pady=5, sticky="ew")
            ctk.CTkLabel(frame, text=key.replace("_", " "), width=200, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(frame, width=400, show="*" if "KEY" in key else "")
            entry.insert(0, str(_get(key)))
            entry.pack(side="right", expand=True, fill="x", padx=10)
            self.env_entries[key] = entry
        
        # Legal Compliance (Phase 32)
        legal_frame = ctk.CTkFrame(self.settings_frame, fg_color="#2c3e50", corner_radius=10)
        legal_frame.grid(row=90, column=0, padx=30, pady=20, sticky="ew")
        
        ctk.CTkLabel(legal_frame, text="⚠️ LEGAL ACKNOWLEDGEMENT", font=ctk.CTkFont(weight="bold", size=12)).pack(pady=(10, 5))
        ctk.CTkLabel(legal_frame, text="This tool is for educational purposes. I accept full responsibility for all activities\nand acknowledge the risk of account suspension on third-party platforms.", font=ctk.CTkFont(size=11), text_color="gray90").pack(pady=5)
        
        self.legal_check = ctk.CTkCheckBox(legal_frame, text="I AGREE TO THE TERMS & DISCLAIMER", variable=self.legal_var, command=self.toggle_legal_lock, progress_color="#e74c3c")
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
        ctk.CTkLabel(self.support_frame, text="Help & Community Hub", font=ctk.CTkFont(size=26, weight="bold")).grid(row=0, column=0, padx=30, pady=30, sticky="w")
        box = ctk.CTkFrame(self.support_frame, corner_radius=15); box.grid(row=1, column=0, padx=30, pady=10, sticky="ew")
        ctk.CTkLabel(box, text="JobBot Community", font=ctk.CTkFont(weight="bold")).pack(pady=10)
        ctk.CTkButton(box, text="📂 GitHub Repository", command=lambda: webbrowser.open(f"https://github.com/{config.GITHUB_REPO}")).pack(pady=10)
        self.feedback_text = ctk.CTkTextbox(box, height=150); self.feedback_text.pack(fill="x", padx=30, pady=10)

        ctk.CTkButton(box, text="🚀 TRANSMIT FEEDBACK", command=self.send_feedback, fg_color="#3498db").pack(pady=20)

    def select_frame_by_name(self, name):
        # Update Nav Styles
        nav_map = {"Dashboard": self.dashboard_btn, "Search": self.search_btn, "Assets": self.assets_btn, 
                   "Analytics": self.analytics_btn, "Settings": self.settings_btn, "Support": self.support_btn}
        for n, b in nav_map.items():
            b.configure(fg_color="#34495e" if n == name else "transparent", border_width=1 if n == name else 0)

        # Swap Frames
        frame_map = {"Dashboard": self.dashboard_frame, "Search": self.search_frame, "Assets": self.assets_frame,
                     "Analytics": self.analytics_frame, "Settings": self.settings_frame, "Support": self.support_frame}
        for n, f in frame_map.items():
            if n == name:
                f.grid(row=0, column=1, sticky="nsew")
                if n == "Dashboard": self.refresh_job_feed()
                if n == "Analytics": self._draw_analytics_chart()
            else: f.grid_forget()

    def show_dashboard(self): self.select_frame_by_name("Dashboard")
    def show_search(self): self.select_frame_by_name("Search")
    def show_assets(self): self.select_frame_by_name("Assets")
    def show_analytics(self): self.select_frame_by_name("Analytics")
    def show_settings(self): self.select_frame_by_name("Settings")
    def show_support(self): self.select_frame_by_name("Support")

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
            score_color = "#2ecc71" if app.match_score >= 85 else "#f1c40f" if app.match_score >= 70 else "#e74c3c"
            score_label = ctk.CTkLabel(row, text=f"{app.match_score}%", text_color=score_color, font=ctk.CTkFont(size=11, weight="bold"), width=35)
            score_label.pack(side="left", padx=2)
            
            # 3. Job Info
            info_text = f"{app.company[:12]} | {app.job_title[:22]}..."
            ctk.CTkLabel(row, text=info_text, font=ctk.CTkFont(size=11), anchor="w").pack(side="left", padx=5, pady=10)
            
            # 4. Action Buttons
            if app.status == "new":
                ctk.CTkButton(row, text="APPLY NOW", width=80, height=26, fg_color="#27ae60", hover_color="#2ecc71", 
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
        env_path = PROJECT_ROOT / ".env"
        for k, e in self.env_entries.items():
            if e.get(): set_key(str(env_path), k, e.get())
        print("[Core] System configuration synchronized.")

    def run_pipeline(self):
        self.status_indic.configure(text="● ACTIVE", text_color="#f1c40f")
        def _run():
            from main import run_auto_pipeline
            try: 
                run_auto_pipeline()
            finally: 
                # Phase 24.1: Thread-safe UI updates
                self.after(0, lambda: self.status_indic.configure(text="● READY", text_color="#2ecc71"))
                self.after(0, self.refresh_stats)
        threading.Thread(target=_run, daemon=True).start()

    def run_semi_auto_search(self):
        kw, loc, plat = self.search_keywords.get(), self.search_location.get(), self.search_platform.get().lower()
        if not kw or not loc: return
        def _run():
            from main import run_search_pipeline
            try: 
                run_search_pipeline(plat, kw, [loc], limit=5)
            finally:
                # Phase 24.1: Thread-safe UI updates
                self.after(0, self.refresh_stats)
        threading.Thread(target=_run, daemon=True).start()


    def send_feedback(self):
        msg = self.feedback_text.get("0.0", "end").strip()
        if not msg: return
        from src.feedback import send_discord_feedback
        if send_discord_feedback(msg): self.feedback_text.delete("0.0", "end")

    def on_closing(self):
        """Restore stdout and close the app."""
        sys.stdout = self._old_stdout
        self.destroy()

if __name__ == "__main__":
    JobAutomationApp().mainloop()

