"""
Job Automation System - Main CLI Orchestrator
Rich-powered interactive menu + fully automated pipeline mode.

Usage:
    python main.py              Interactive menu
    python main.py --auto       Fully automated pipeline (no prompts)
    python main.py --auto -d 7  Auto mode, scan last 7 days
"""

import sys
import time
import argparse
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

import config
from src.email_scanner import EmailScanner, JobAlert
from src.resume_builder import generate_documents, parse_resume
from src.tracker import Tracker
from src.applicant_bot import apply_to_job, cleanup_bots, cleanup_browser_processes
from src.llm_provider import get_llm, switch_provider, test_connection
from src.applicant_profile import ApplicantProfile, launch_wizard
from src.maintenance import purge_old_outputs

import atexit
atexit.register(cleanup_bots)  # Always close browsers on exit

console = Console()
console.print("[bold yellow][System] GUI & Navigation Hotfix v2.0 Applied.[/]")
tracker = Tracker()


# ── Helpers ──────────────────────────────────────────────────

def _safe_print(msg):
    """Helper to print messages using Rich console for styling."""
    console.print(msg)

def _display_applications(apps: list, title: str = "Applications", max_rows: int = 30):
    """Display applications in a formatted table."""
    table = Table(title=title, box=box.SIMPLE_HEAVY, padding=(0, 1))
    table.add_column("#", style="bold yellow", width=4, justify="right")
    table.add_column("Job Title", style="bold white", max_width=40)
    table.add_column("Company", style="cyan", max_width=20)
    table.add_column("Source", style="magenta", width=10)
    table.add_column("Status", width=12)
    table.add_column("Match", width=7, justify="right")

    status_styles = {
        "new": "[white]new[/]",
        "applied": "[bold green]applied[/]",
        "interview": "[bold cyan]interview[/]",
        "rejected": "[dim red]rejected[/]",
        "offer": "[bold green on black] OFFER [/]",
        "manual_apply_needed": "[yellow]manual[/]",
        "skipped": "[dim]skipped[/]",
        "error": "[red]error[/]",
    }

    display_apps = apps[:max_rows]
    for i, app in enumerate(apps[:max_rows], 1):
        status_display = status_styles.get(app.status, f"[white]{app.status}[/]")
        score = app.match_score
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        table.add_row(
            str(i),
            (app.job_title or "Untitled")[:40],
            (app.company or "-")[:20],
            app.source or "-",
            status_display,
            f"[{score_color}]{score}%[/]",
        )

    console.print(table)
    if len(apps) > max_rows:
        console.print(f"  [dim]... and {len(apps) - max_rows} more[/]\n")


def _display_alerts(alerts: list[JobAlert], max_rows: int = 30):
    """Display job alerts in a compact table."""
    table = Table(
        title=f"[bold]Found {len(alerts)} Job Alerts[/]",
        box=box.SIMPLE_HEAVY,
        padding=(0, 1),
    )
    table.add_column("#", style="bold yellow", width=4, justify="right")
    table.add_column("Job Title", style="bold white", max_width=40)
    table.add_column("Company", style="cyan", max_width=20)
    table.add_column("Source", style="magenta", width=10)
    table.add_column("Match", width=7, justify="right")

    for i, alert in enumerate(alerts[:max_rows], 1):
        score = alert.match_score
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        table.add_row(
            str(i),
            (alert.job_title or "Untitled")[:40],
            (alert.company or "-")[:20],
            alert.source,
            f"[{score_color}]{score}%[/]",
        )

    console.print(table)
    if len(alerts) > max_rows:
        console.print(f"  [dim]... and {len(alerts) - max_rows} more[/]\n")


# ── Banner ───────────────────────────────────────────────────

def show_banner():
    """Display the application banner."""
    banner = """
     ╦╔═╗╔╗   ╔═╗╦ ╦╔╦╗╔═╗╔╦╗╔═╗╔╦╗╦╔═╗╔╗╔
     ║║ ║╠╩╗  ╠═╣║ ║ ║ ║ ║║║║╠═╣ ║ ║║ ║║║║
    ╚╝╚═╝╚═╝  ╩ ╩╚═╝ ╩ ╚═╝╩ ╩╩ ╩ ╩ ╩╚═╝╝╚╝
    """
    console.print(Panel(
        f"{banner}\n[dim center][bold cyan]Bot Engine v25.0.0[/] | [dim]Direct Search Upgrade[/][/]",
        style="bold cyan",
        box=box.DOUBLE,
        subtitle="[bold yellow]Stability Phase 24[/]"
    ))
    console.print(config.summary())
    console.print()


def show_menu() -> str:
    """Display the modern, grouped main menu."""
    from rich.columns import Columns

    def make_section(title, items, color="cyan"):
        t = Table(box=None, show_header=False, padding=(0, 1))
        t.add_column("ID", style=f"bold {color}", width=3)
        t.add_column("Action", style="white")
        for i, text in items:
            t.add_row(i, text)
        return Panel(t, title=f"[{color}]{title}[/]", border_style=color, padding=(0, 1))

    # Define Sections - Chronologically Organized
    config_section = make_section("⚙️ [bold]1. Setup & Profile[/]", [
        ("1", "Profile Setup Wizard"),
        ("2", "Switch AI Provider"),
        ("3", "Test AI Connection"),
    ], "magenta")
    
    pipeline = make_section("🚀 [bold]2. Find Jobs[/]", [
        ("4", "Scan Email Alerts"),
        ("5", "Direct Search & Apply (Auto)"),
        ("6", "Semi-Autonomous Search (Manual Apply)"),
        ("7", "Full Pipeline (100% Auto)"),
    ], "green")

    docs = make_section("📄 [bold]3. Documents[/]", [
        ("8", "Generate tailored Resumes"),
        ("9", "View Application Tracker"),
        ("10", "Success Stats & Analytics"),
    ], "blue")

    tools = make_section("🛠 [bold]4. Maintenance & Tools[/]", [
        ("11", "Purge Documents"),
        ("12", "Launch GUI"),
        ("0", "Exit"),
    ], "yellow")

    console.print(Columns([config_section, pipeline, docs, tools], equal=True, expand=True))
    
    return Prompt.ask("\n[bold cyan]Choose[/]", choices=[str(i) for i in range(13)])



# ═══════════════════════════════════════════════════════════════
#  FULLY AUTOMATED PIPELINE (--auto mode)
# ═══════════════════════════════════════════════════════════════

def run_auto_pipeline(days_back: float = 3):
    """
    Fully automated pipeline — zero prompts.
    Scan email -> filter -> track -> generate docs -> apply to all.
    """
    show_banner()
    console.print(Panel(
        "[bold]FULLY AUTOMATED MODE[/]\n"
        "Scan email -> Track -> Generate docs -> Apply",
        style="bold green",
        box=box.HEAVY,
    ))

    # ── Step 1: Scan ──
    console.print("\n[bold cyan]Step 1/4[/] [bold]Scanning email...[/]")
    if not config.YAHOO_EMAIL or not config.YAHOO_APP_PASSWORD:
        console.print("[red]  Yahoo email not configured in .env — cannot proceed.[/]")
        return

    if config.TARGET_ROLES:
        console.print(f"  Target roles: [cyan]{', '.join(config.TARGET_ROLES)}[/]")

    scanner = EmailScanner()
    alerts = scanner.scan(days_back=days_back, filter_roles=bool(config.TARGET_ROLES))
    scanner.disconnect()

    if not alerts:
        console.print("[yellow]  No new job alerts found. Nothing to do.[/]")
        return

    _display_alerts(alerts)

    # ── Step 2: Track ──
    console.print(f"\n[bold cyan]Step 2/4[/] [bold]Adding {len(alerts)} jobs to tracker...[/]")
    new_count = 0
    skipped_duplicates = 0
    skip_statuses = ["applied", "interview", "offer", "manual_apply_needed", "rejected", "skipped"]
    for alert in alerts:
        # Check if already applied or tracked
        existing = tracker.find_by_url(alert.apply_url)
        if existing and existing.status in skip_statuses:
            skipped_duplicates += 1
            continue

        result_id = tracker.add(
            job_title=alert.job_title,
            company=alert.company,
            location=alert.location,
            description=alert.description,
            apply_url=alert.apply_url,
            source=alert.source,
            match_score=alert.match_score,
        )
        if result_id:
            new_count += 1
            
    # Refresh alerts to only process new ones
    alerts = [a for a in alerts if not tracker.find_by_url(a.apply_url) or tracker.find_by_url(a.apply_url).status not in skip_statuses]
    
    console.print(f"  [green]{new_count} jobs tracked[/] ({skipped_duplicates} duplicates skipped)")

    # ── Step 3: Generate docs ──
    console.print(f"\n[bold cyan]Step 3/4[/] [bold]Generating tailored documents...[/]")
    doc_success = 0
    doc_fail = 0
    consecutive_fails = 0

    for i, alert in enumerate(alerts, 1):
        # Stop trying if LLM is clearly broken
        if consecutive_fails >= 10:
            console.print(f"\n  [yellow]LLM appears to be down — skipping remaining {len(alerts) - i + 1} jobs.[/]")
            doc_fail += len(alerts) - i + 1
            break

        console.print(f"  [{i}/{len(alerts)}] {alert.job_title[:50]}...", end=" ")
        try:
            app = tracker.find_by_url(alert.apply_url)
            
            # Phase 27.2: Skip if docs already exist (Persistence)
            if app and app.resume_path and Path(app.resume_path).exists():
                console.print("[blue]using existing docs[/]")
                doc_success += 1
                continue

            # Skip list/search pages 
            if any(x in alert.apply_url.lower() for x in ["/search/", "/collections/", "/jobs/search"]):
                console.print(f"[yellow]skipped (job list page)[/]")
                if app:
                    tracker.update_status(app.id, "skipped", "Not a single job page")
                doc_fail += 1
                continue

            paths = generate_documents(
                alert.job_title, alert.company, alert.location, alert.description
            )
            if app:
                tracker.update_documents(
                    app.id,
                    resume_path=str(paths.get("resume_pdf", "")),
                    cover_letter_path=str(paths.get("cover_letter_pdf", "")),
                )
            doc_success += 1
            consecutive_fails = 0
            console.print("[green]done[/]")
        except Exception as e:
            doc_fail += 1
            # Only count as 'consecutive fail' if it wasn't a timeout (which might be transient)
            if "timeout" not in str(e).lower():
                consecutive_fails += 1
            console.print(f"[red]failed ({e})[/]")

    console.print(f"  [green]{doc_success} generated[/]", end="")
    if doc_fail:
        console.print(f" | [red]{doc_fail} failed[/]")
    else:
        console.print()

    # ── Step 4: Auto-apply ──
    cleanup_browser_processes() # Surgical Phase 25.1 cleanup
    console.print(f"\n[bold cyan]Step 4/4[/] [bold]Auto-applying to jobs...[/]")

    resume_text = ""
    try:
        resume_text = parse_resume()
    except FileNotFoundError:
        console.print("  [yellow]No base resume found — skipping question answering[/]")

    applied = 0
    failed = 0
    skipped = 0

    for i, alert in enumerate(alerts, 1):
        app = tracker.find_by_url(alert.apply_url)
        if not app:
            continue

        # Skip already-applied or manual-intervention jobs
        if app.status in skip_statuses:
            skipped += 1
            continue

        console.print(f"  [{i}/{len(alerts)}] {alert.job_title[:45]} ({alert.source})...", end=" ")

        # Verify documents exist before applying
        if not app.resume_path or not Path(app.resume_path).exists():
            print(f"[yellow]skipped (resume not found at {app.resume_path})[/]")
            skipped += 1
            tracker.update_status(app.id, "error", "Tailored resume not found")
            continue

        result = apply_to_job(
            apply_url=alert.apply_url,
            resume_path=app.resume_path,
            cover_letter_path=app.cover_letter_path if app.cover_letter_path else "",
            resume_text=resume_text,
            source=alert.source,
        )

        if result["success"]:
            applied += 1
            tracker.update_status(app.id, "applied", result["message"])
            console.print("[green]applied![/]")
        elif "manual intervention" in result["message"].lower() or "external form filled" in result["message"].lower():
            tracker.update_status(app.id, "manual_apply_needed", result["message"])
            console.print(f"[yellow]{result['message'][:40]}...[/]")
        else:
            failed += 1
            tracker.update_status(app.id, "error", result["message"])
            console.print(f"[red]failed ({result['message'][:40]})[/]")

    # ── Summary ──
    console.print(Panel(
        f"[bold]Pipeline Complete![/]\n\n"
        f"  Jobs found:    {len(alerts)}\n"
        f"  Docs created:  {doc_success}\n"
        f"  Applied:       [green]{applied}[/]\n"
        f"  Failed:        [red]{failed}[/]\n"
        f"  Skipped:       {skipped}",
        style="green",
        box=box.HEAVY,
    ))


# ═══════════════════════════════════════════════════════════════
#  INTERACTIVE MENU ACTIONS
# ═══════════════════════════════════════════════════════════════

def action_scan_email():
    """Scan Yahoo email for job alerts."""
    console.print("\n[bold]Scanning Yahoo Mail...[/]\n")

    if not config.YAHOO_EMAIL or not config.YAHOO_APP_PASSWORD:
        console.print("[red]  Yahoo email not configured. Set YAHOO_EMAIL and YAHOO_APP_PASSWORD in .env[/]")
        return

    if config.TARGET_ROLES:
        console.print(f"  Target roles: [cyan]{', '.join(config.TARGET_ROLES)}[/]")
    else:
        console.print("  [dim]No TARGET_ROLES set — showing all jobs[/]")
    try:
        days_back = float(Prompt.ask("  Days to search back (e.g. 0.1 for ~2.4h)", default="3"))
    except ValueError:
        days_back = 3.0
    scanner = EmailScanner()
    alerts = scanner.scan(days_back=days_back, filter_roles=bool(config.TARGET_ROLES))
    scanner.disconnect()

    if not alerts:
        console.print("\n[yellow]  No job alerts found.[/]")
        return

    _display_alerts(alerts)

    # Auto-track all found jobs
    for alert in alerts:
        tracker.add(
            job_title=alert.job_title,
            company=alert.company,
            location=alert.location,
            description=alert.description,
            apply_url=alert.apply_url,
            source=alert.source,
            match_score=alert.match_score,
        )
    console.print(f"[green]  All {len(alerts)} jobs added to tracker automatically.[/]")


def action_generate_docs():
    """Generate tailored resume and cover letter for a job."""
    console.print("\n[bold]Generate Tailored Resume & Cover Letter[/]\n")

    apps = tracker.get_all()
    if not apps:
        console.print("[yellow]  No tracked jobs. Scan email first (option 1).[/]")
        return

    _display_applications(apps, title="Select a Job")
    choice = IntPrompt.ask("\n  Job #", default=1)

    if 1 <= choice <= len(apps):
        app = apps[choice - 1]
        console.print(f"\n  Generating for: [cyan]{app.job_title}[/] @ [cyan]{app.company}[/]")
        try:
            paths = generate_documents(
                app.job_title, app.company, app.location, app.description
            )
            console.print(f"\n[green]  Done! Saved to: {paths['output_dir']}[/]")
            tracker.update_documents(
                app.id,
                resume_path=str(paths.get("resume_pdf", "")),
                cover_letter_path=str(paths.get("cover_letter_pdf", "")),
            )
        except Exception as e:
            console.print(f"[red]  Error: {e}[/]")
    else:
        console.print("[red]  Invalid selection[/]")


def action_auto_apply():
    """Apply to tracked jobs automatically."""
    console.print("\n[bold]Auto Apply[/]\n")

    apps = tracker.get_by_status("new")
    if not apps:
        console.print("[yellow]  No new jobs to apply to.[/]")
        return

    _display_applications(apps, title="New Jobs Ready to Apply")
    console.print(f"\n  [bold]{len(apps)} jobs ready.[/]")
    mode = Prompt.ask("  Apply to [a]ll or pick [#]?", default="a")

    resume_text = ""
    try:
        resume_text = parse_resume()
    except FileNotFoundError:
        pass

    if mode.lower() == "a":
        # Apply to ALL
        targets = apps
    else:
        try:
            idx = int(mode) - 1
            targets = [apps[idx]] if 0 <= idx < len(apps) else []
        except ValueError:
            console.print("[red]  Invalid input[/]")
            return

    for app in targets:
        console.print(f"\n  Applying: [cyan]{app.job_title}[/] ({app.source})")
        
        # Phase 26.0: Match Score Threshold Filter
        if app.match_score < config.MATCH_SCORE_THRESHOLD:
            console.print(f"  [yellow]Skipped: Match score ({app.match_score}%) too low (Threshold: {config.MATCH_SCORE_THRESHOLD}%)[/]")
            continue

        # Verify documents exist
        if not app.resume_path or not Path(app.resume_path).exists():
            console.print(f"  [yellow]Skipped: Tailored resume not found at {app.resume_path}[/]")
            tracker.update_status(app.id, "error", "Tailored resume not found")
            continue

        result = apply_to_job(
            apply_url=app.apply_url,
            resume_path=app.resume_path,
            cover_letter_path=app.cover_letter_path,
            resume_text=resume_text,
            source=app.source,
        )

        if result["success"]:
            console.print(f"  [green]Applied![/]")
            tracker.update_status(app.id, "applied", result["message"])
        else:
            console.print(f"  [yellow]{result['message']}[/]")
            tracker.update_status(app.id, "error", result["message"])


def action_view_tracker():
    """View all tracked applications."""
    console.print("\n[bold]Application Tracker[/]\n")

    status_filter = Prompt.ask(
        "  Filter by status",
        choices=["all"] + Tracker.STATUSES,
        default="all",
    )

    apps = tracker.get_all() if status_filter == "all" else tracker.get_by_status(status_filter)

    if not apps:
        console.print("[yellow]  No applications found.[/]")
        return

    _display_applications(apps, title=f"Applications ({status_filter})", max_rows=50)

    # Phase 26.0: Semi-Autonomous Surgical UI
    action = Prompt.ask("\n  [a]pply specific, [v]iew details, or [q]uit", choices=["a", "v", "q"], default="q")
    if action == "q": return
    
    choice = IntPrompt.ask("  Application #", default=1)
    if 1 <= choice <= len(apps):
        app = apps[choice - 1]
        
        if action == "v":
            console.print(Panel(f"[bold]{app.job_title}[/]\n{app.company} | {app.location}\nMatch: {app.match_score}%\n\n{app.description[:500]}...", title="Job Details"))
        elif action == "a":
            resume_text = ""
            try: resume_text = parse_resume()
            except: pass
            
            console.print(f"\n  [bold yellow]Surgical Apply:[/][cyan] {app.job_title}[/]...")
            result = apply_to_job(app.apply_url, app.resume_path, app.cover_letter_path, resume_text, app.source)
            if result["success"]:
                tracker.update_status(app.id, "applied", result["message"])
                console.print("[green]Applied![/]")
            else:
                console.print(f"[red]Error: {result['message']}[/]")


def action_update_status():
    """Update the status of a tracked application."""
    console.print("\n[bold]Update Application Status[/]\n")

    apps = tracker.get_all()
    if not apps:
        console.print("[yellow]  No tracked applications.[/]")
        return

    _display_applications(apps, title="Select Application")
    choice = IntPrompt.ask("\n  Application #", default=1)

    if 1 <= choice <= len(apps):
        app = apps[choice - 1]
        console.print(f"\n  [cyan]{app.job_title}[/] — currently: [yellow]{app.status}[/]")

        new_status = Prompt.ask("  New status", choices=Tracker.STATUSES, default=app.status)
        notes = Prompt.ask("  Notes (optional)", default="")
        tracker.update_status(app.id, new_status, notes)
        console.print(f"[green]  Updated to: {new_status}[/]")
    else:
        console.print("[red]  Invalid selection[/]")


def action_switch_llm():
    """Switch LLM provider at runtime."""
    console.print(f"\n  Current: [cyan]{config.LLM_PROVIDER}[/]")
    
    new_provider = Prompt.ask(
        "  Select",
        choices=["openai", "ollama", "lmstudio", "gemini", "claude", "groq", "openrouter"],
        default=config.LLM_PROVIDER,
    )

    try:
        switch_provider(new_provider)
        config.LLM_PROVIDER = new_provider
        console.print(f"[green]  Switched to: {new_provider}[/]")
    except Exception as e:
        console.print(f"[red]  Error: {e}[/]")


def action_full_pipeline():
    """Full pipeline in interactive mode — with progress updates, no per-job prompts."""
    try:
        days_back = float(Prompt.ask("  Days to search back (e.g. 0.1 for ~2.4h)", default="3"))
    except ValueError:
        days_back = 3.0
    run_auto_pipeline(days_back=days_back)


def action_direct_search():
    """Perform a direct job search and apply."""
    console.print("\n[bold]Direct Search & Apply[/]\n")
    
    platform = Prompt.ask("  Platform", choices=["linkedin", "indeed", "both"], default="both")
    
    # Use profile info as defaults if available
    profile = ApplicantProfile()
    personal = profile.data.get("personal", {})
    experience = profile.data.get("experience", {})
    
    default_role = config.TARGET_ROLES[0] if config.TARGET_ROLES else experience.get("current_title", "")
    default_loc = f"{personal.get('city', '')}, {personal.get('country', '')}"
    
    keywords = Prompt.ask("  Job Role / Keywords", default=default_role)
    location_input = Prompt.ask("  Location (comma-separated for multi-search)", default=default_loc)
    limit = IntPrompt.ask("  Max jobs to find per location", default=10)
    
    locations = [loc.strip() for loc in location_input.split(",") if loc.strip()]
    if not locations:
        locations = [default_loc]
        
    run_search_pipeline(platform, keywords, locations, limit)


def run_search_pipeline(platform: str, keywords: str, locations: list[str], limit: int = 10):
    """
    Search LinkedIn/Indeed directly, track results, and apply.
    """
    show_banner()
    loc_str = ", ".join(locations)
    console.print(Panel(
        f"[bold]DIRECT SEARCH & APPLY MODE[/]\n"
        f"Platform: [cyan]{platform}[/] | Role: [cyan]{keywords}[/] | Locs: [cyan]{loc_str}[/]",
        style="bold blue",
        box=box.HEAVY,
    ))

    from src.applicant_bot import LinkedInBot, IndeedBot, quit_all_bots, _short_delay
    
    quit_all_bots()
    time.sleep(2.0)
    
    all_jobs = []
    profile = ApplicantProfile()

    
    for location in locations:
        console.print(f"\n  [bold yellow]📍 Location: {location}[/]")
        
        # Phase 35.2: Unified Platform Iterator
        # Supported: linkedin, indeed, ziprecruiter, dice, wellfound, builtin
        target_plats = []
        if platform.lower() == "both":
            target_plats = ["linkedin", "indeed"]
        else:
            target_plats = [platform.lower()]
            
        from src.applicant_bot import get_bot
        
        for p in target_plats:
            # Skip if bot manager doesn't handle it
            try:
                # Surgical Fix: get_bot expects (url, platform), profile is handled internally
                bot = get_bot(f"https://{p}.com", platform=p)
                if not bot: continue
                
                _safe_print(f"  🔍 Searching [cyan]{p}[/] for [cyan]{keywords}[/]...")
                results = bot.search(keywords, location, limit=limit)
                all_jobs.extend(results)
                # Note: We don't quit here, we let the singleton manager handle it or final quit_all
                _short_delay()
            except Exception as e:
                console.print(f"[red]  {p.capitalize()} search failed for {location}: {e}[/]")

    # Phase 25.1: Clean up after search as well to release all ports for Step 4
    quit_all_bots()
    time.sleep(2.0)

    if not all_jobs:
        console.print("[yellow]  No jobs found via direct search. Try different keywords.[/]")
        return
    # Convert to JobAlert-like objects for the display helper
    from src.email_scanner import JobAlert
    from datetime import datetime
    
    alerts = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    for j in all_jobs:
        alerts.append(JobAlert(
            job_title=j["job_title"],
            company=j["company"],
            location=j.get("location", "Remote/Various"),
            apply_url=j["apply_url"],
            description="", 
            source=j["source"],
            email_date=timestamp,
            email_subject=f"Direct Search: {keywords}",
            match_score=85 
        ))
    
    _display_alerts(alerts)

    # ── Step 2-4: Run standard auto pipeline logic ──
    console.print(f"\n[bold cyan]Step 2/4[/] [bold]Adding {len(alerts)} jobs to tracker...[/]")
    new_count = 0
    for alert in alerts:
        res = tracker.add(
            job_title=alert.job_title,
            company=alert.company,
            location=alert.location,
            description=alert.description,
            apply_url=alert.apply_url,
            source=alert.source,
            match_score=alert.match_score
        )
        if res: new_count += 1
    console.print(f"  [green]{new_count} jobs tracked[/]")

    console.print(f"\n[bold cyan]Step 3/4[/] [bold]Generating tailored documents...[/]")
    doc_success = 0
    for i, alert in enumerate(alerts, 1):
        console.print(f"  [{i}/{len(alerts)}] {alert.job_title[:50]}...", end=" ")
        try:
            generate_documents(alert.job_title, alert.company, alert.location, "")
            doc_success += 1
            console.print("[green]done[/]")
        except:
            console.print("[red]failed[/]")

    console.print(f"\n[bold cyan]Step 4/4[/] [bold]Auto-applying to jobs...[/]")
    applied = 0
    resume_text = ""
    try: from src.resume_builder import parse_resume; resume_text = parse_resume()
    except: pass

    for i, alert in enumerate(alerts, 1):
        app = tracker.find_by_url(alert.apply_url)
        if not app or app.status == "applied": continue
        
        console.print(f"  [{i}/{len(alerts)}] {alert.job_title[:45]}...", end=" ")
        result = apply_to_job(alert.apply_url, app.resume_path, "", resume_text, alert.source)
        if result["success"]:
            applied += 1
            tracker.update_status(app.id, "applied")
            console.print("[green]applied![/]")
        else:
            console.print(f"[red]failed ({result['message'][:30]})[/]")

    console.print(Panel(f"Search & Apply Complete!\nApplied: [bold green]{applied}[/]", style="green"))


def action_semi_autonomous_search():
    """Perform a job search, generate docs, but present a dashboard instead of auto-applying."""
    console.print("\n[bold]Semi-Autonomous Search (Manual Apply)[/]\n")
    
    platform = Prompt.ask("  Platform", choices=["linkedin", "indeed", "both"], default="both")
    
    profile = ApplicantProfile()
    personal = profile.data.get("personal", {})
    experience = profile.data.get("experience", {})
    
    default_role = config.TARGET_ROLES[0] if config.TARGET_ROLES else experience.get("current_title", "")
    default_loc = f"{personal.get('city', '')}, {personal.get('country', '')}"
    
    keywords = Prompt.ask("  Job Role / Keywords", default=default_role)
    location_input = Prompt.ask("  Location (comma-separated for multi-search)", default=default_loc)
    limit = IntPrompt.ask("  Max jobs to find per location", default=5)
    
    locations = [loc.strip() for loc in location_input.split(",") if loc.strip()]
    if not locations:
        locations = [default_loc]
        
    show_banner()
    console.print(Panel(
        f"[bold]SEMI-AUTONOMOUS MODE[/]\nFinding and tailoring documents without applying.",
        style="bold purple", box=box.HEAVY
    ))

    # Search
    from src.applicant_bot import LinkedInBot, IndeedBot, quit_all_bots
    quit_all_bots()
    time.sleep(2.0)
    
    all_jobs = []
    for location in locations:
        console.print(f"\n  [bold yellow]📍 Location: {location}[/]")
        if platform.lower() in ["linkedin", "both"]:
            try:
                li_bot = LinkedInBot(profile=profile)
                all_jobs.extend(li_bot.search(keywords, location, limit=limit))
                li_bot.quit()
            except Exception as e:
                console.print(f"[red]  LinkedIn search failed: {e}[/]")
        if platform.lower() in ["indeed", "both"]:
            try:
                in_bot = IndeedBot(profile=profile)
                all_jobs.extend(in_bot.search(keywords, location, limit=limit))
                in_bot.quit()
            except Exception as e:
                console.print(f"[red]  Indeed search failed: {e}[/]")

    quit_all_bots()
    if not all_jobs:
        console.print("[yellow]  No jobs found via direct search.[/]")
        return
        
    from src.email_scanner import JobAlert
    from datetime import datetime
    alerts = []
    for j in all_jobs:
        alerts.append(JobAlert(
            job_title=j["job_title"], company=j["company"], location=j.get("location", "Remote/Various"),
            apply_url=j["apply_url"], description="", source=j["source"], email_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            email_subject="Semi-Autonomous Search", match_score=85 
        ))
    
    # Track Jobs & Generate Docs
    console.print(f"\n[bold cyan]Processing {len(alerts)} jobs...[/]")
    generated_folders = []
    for i, alert in enumerate(alerts, 1):
        tracker.add(alert.job_title, alert.company, alert.location, alert.description, alert.apply_url, alert.source, alert.match_score)
        
        console.print(f"  [{i}/{len(alerts)}] {alert.job_title[:45]}...", end=" ")
        try:
            paths = generate_documents(alert.job_title, alert.company, alert.location, "")
            generated_folders.append((alert, str(paths["output_dir"])))
            console.print("[green]Tailored![/]")
        except:
            generated_folders.append((alert, "Failed"))
            console.print("[red]Failed[/]")

    # Present Dashboard
    console.print("\n[bold purple]📋 Your Application Dashboard[/]\n")
    console.print("  [dim]Review the tailored documents below, then click the job link to manually apply.[/]\n")
    
    dashboard = Table(box=box.SIMPLE_HEAVY)
    dashboard.add_column("Company - Title", style="cyan", max_width=45)
    dashboard.add_column("Apply Link", style="blue")
    dashboard.add_column("Document Folder Path", style="dim green", max_width=60)
    
    for alert, folder in generated_folders:
        dashboard.add_row(f"{alert.company} - {alert.job_title}", f"[link={alert.apply_url}]Click to Apply[/link]", folder)
        
def action_stats():
    """Show detailed application analytics dashboard."""
    stats = tracker.get_analytics()

    if stats["total"] == 0:
        console.print("\n[yellow]  No applications tracked yet.[/]")
        return

    console.print("\n[bold cyan]📊 Application Analytics Dashboard[/bold cyan]")
    
    # Summary Table
    summary = Table(box=box.ROUNDED)
    summary.add_column("Metric", style="cyan")
    summary.add_column("Value", style="bold white")
    
    summary.add_row("Total Jobs Found", str(stats["total"]))
    summary.add_row("Jobs Applied", f"[green]{stats['applied']}[/green]")
    summary.add_row("Success Rate", f"{stats['success_rate']}%")
    summary.add_row("New Jobs (Last 7 Days)", str(stats["recent_7_days"]))
    
    # Status breakdown
    status_table = Table(title="Status Breakdown", box=box.SIMPLE)
    status_table.add_column("Status", style="magenta")
    status_table.add_column("Count", justify="right")
    for s, c in stats["statuses"].items():
        status_table.add_row(s, str(c))
        
    # Platform breakdown
    platform_table = Table(title="Platform Breakdown", box=box.SIMPLE)
    platform_table.add_column("Platform", style="yellow")
    platform_table.add_column("Count", justify="right")
    for p, c in stats["platforms"].items():
        platform_table.add_row(p, str(c))

    # Layout
    from rich.columns import Columns
    console.print(summary)
    console.print(Columns([status_table, platform_table]))
    input("\nPress Enter to return...")

def action_purge():
    """Purge old generated documents to save space."""
    console.print("\n[bold]Purge Old Documents[/]\n")
    try:
        days = IntPrompt.ask("Keep documents from the last how many days? (0 to wipe all)", default=14)
        if Confirm.ask(f"Are you sure you want to delete output folders older than {days} days?", default=False):
            with console.status(f"[bold red]Purging files older than {days} days..."):
                deleted, space = purge_old_outputs(days)
            console.print(f"  [green]Success![/] Removed [bold]{deleted}[/] folders, freeing [bold]{space} MB[/].")
    except Exception as e:
        console.print(f"[red]Error purging: {e}[/]")


def action_test_llm():
    """Test the current LLM connection with real-time visuals."""
    provider = config.LLM_PROVIDER
    console.print(f"\n[bold]Testing {provider} Connection...[/]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        # Step 1: Initializing
        task1 = progress.add_task(f"  [cyan]Initializing {provider} provider...", total=None)
        time.sleep(0.5)
        
        # Step 2: Connection
        progress.update(task1, description=f"  [yellow]Connecting to {provider} & loading model...")
        try:
            llm = get_llm(resilient=False)
            start_time = time.time()
            response = llm.generate("Say 'Hello!' in exactly one word. Use no punctuation.", "You are a minimal assistant.")
            elapsed = time.time() - start_time
            
            if response and "hello" in response.lower():
                progress.update(task1, description="  [green]Parsing response...")
                time.sleep(0.3)
                console.print(f"  [bold green]✓ Success![/] [dim]({elapsed:.2f}s)[/]")
                console.print(Panel(f"[italic]'{response}'[/]", title="LLM Response", border_style="green", expand=False))
            else:
                console.print(f"  [bold red]✗ Failed![/] [dim]({elapsed:.2f}s)[/]")
                console.print(f"  [red]Provider returned an invalid or empty response: '{response}'[/]")
        except Exception as e:
            console.print(f"  [bold red]✗ Connection Error![/]")
            console.print(f"  [red]Details: {e}[/]")
            console.print(f"\n[yellow]  Check your .env settings for {provider}.[/]")


def launch_gui():
    """Launch the CustomTkinter desktop interface."""
    console.print("\n[bold cyan]Starting GUI Desktop App...[/]")
    time.sleep(1) # PRE-LAUNCH BUFFER
    try:
        from gui import JobAutomationApp
        app = JobAutomationApp()
        app.update_idletasks() # Anti-crash measure for CTk Windows titlebar color
        app.mainloop()
        time.sleep(1) # POST-CLOSE STABILIZATION
    except ImportError as e:
        console.print(f"[red]Failed to launch GUI: {e}. Ensure 'customtkinter' is installed.[/]")
    except Exception as e:
        console.print(f"[red]Error launching GUI: {e}[/]")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Job Automation System")
    parser.add_argument("--auto", action="store_true", help="Fully automated pipeline (no prompts)")
    parser.add_argument("-d", "--days", type=float, default=3.0, help="Days to search back (default: 3)")
    args = parser.parse_args()

    config.validate()
    
    # Phase 22: Cleanup orphaned browsers from previous crashed runs
    cleanup_browser_processes()

    # First-run check: if no profile or missing critical config, offer wizard
    if not config.PROFILE_PATH.exists() or not config.OPENAI_API_KEY and config.LLM_PROVIDER == "openai":
        console.print(Panel(
            "[bold yellow]Welcome![/] It looks like this might be your first time running the system.\n"
            "Would you like to run the [bold cyan]Setup Wizard[/] to configure your profile and API keys?",
            title="Initial Setup"
        ))
        if Confirm.ask("Run Setup Wizard now?", default=True):
            launch_wizard()
            import importlib
            importlib.reload(config)  # Refresh config after wizard

    if args.auto:
        run_auto_pipeline(days_back=args.days)
        return

    # Interactive mode
    show_banner()

    actions = {
        "1": launch_wizard,
        "2": action_switch_llm,
        "3": action_test_llm,
        "4": action_scan_email,
        "5": action_direct_search,
        "6": action_semi_autonomous_search,
        "7": action_full_pipeline,
        "8": action_generate_docs,
        "9": action_view_tracker,
        "10": action_stats,
        "11": action_purge,
        "12": launch_gui,
        "0": lambda: sys.exit(0),
    }

    while True:
        try:
            choice = show_menu()
            actions.get(choice, lambda: None)()
            console.print()
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/]")
            break
        except SystemExit:
            break
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/]")


if __name__ == "__main__":
    main()
