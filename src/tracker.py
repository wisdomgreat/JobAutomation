"""
Application Tracker Module
SQLite-backed database for tracking job applications, statuses, and documents.
"""

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import config


@dataclass
class Application:
    """Represents a tracked job application."""
    id: Optional[int]
    job_title: str
    company: str
    location: str
    description: str
    apply_url: str
    source: str
    status: str  # new, applied, interview, rejected, offer, manual_apply_needed
    resume_path: str
    cover_letter_path: str
    date_found: str
    date_applied: str
    notes: str
    match_score: int
    match_reason: str


class Tracker:
    """SQLite-backed job application tracker."""

    STATUSES = ["new", "applied", "interview", "rejected", "offer", "manual_apply_needed", "skipped", "error"]

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        # Mission Resilience: Upgrade schema and merge legacy data
        self._migrate_db()
        self._check_for_migration()

    def _check_for_migration(self):
        """Surgical check: Merges legacy tracker.db into the official AppData store."""
        legacy_db = Path("data/tracker.db")
        if legacy_db.exists() and legacy_db.resolve() != self.db_path.resolve():
            print(f"[System] Professional Upgrade: Migrating tactical records from {legacy_db.name}...")
            try:
                old_conn = sqlite3.connect(str(legacy_db))
                try:
                    old_conn.row_factory = sqlite3.Row
                    
                    # Phase 34.5: Ensure the legacy table actually exists before reading
                    check = old_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='applications'").fetchone()
                    if not check:
                        print("[System] No legacy 'applications' table detected. Skipping data migration.")
                    else:
                        cursor = old_conn.execute("SELECT * FROM applications")
                        rows = cursor.fetchall()
                        
                        with sqlite3.connect(str(self.db_path)) as new_conn:
                            for row in rows:
                                # Use INSERT OR IGNORE to prevent duplicates based on apply_url
                                new_conn.execute("""
                                    INSERT OR IGNORE INTO applications 
                                    (job_title, company, location, description, apply_url, source, status, 
                                     resume_path, cover_letter_path, date_found, date_applied, notes, match_score, match_reason)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    row['job_title'], row['company'], row['location'], row['description'],
                                    row['apply_url'], row['source'], row['status'], row['resume_path'],
                                    row['cover_letter_path'], row['date_found'], row['date_applied'],
                                    row['notes'], row['match_score'], row.get('match_reason', '')
                                ))
                            new_conn.commit()
                        print(f"[System] Migration successful. {len(rows)} records synchronized.")
                finally:
                    old_conn.close()
                
                # Cleanup: Move legacy file to backup to prevent repeated migrations
                try:
                    backup_path = legacy_db.with_suffix(".db.migrated")
                    # Try to rename. If it fails (WinError 32), we ignore it so the app can start.
                    # The user likely has the file open in an editor or viewer.
                    legacy_db.rename(backup_path)
                    print(f"[System] Legacy database archived to {backup_path.name}")
                except Exception as e:
                    print(f"[Warning] Could not archive legacy database: {e}")
                    print(f"[System] Please close any tools using 'data/tracker.db' to complete the upgrade.")
            except Exception as e:
                print(f"[Warning] Migration interupted: {e}")

    def _ensure_schema(self, func):
        """Decorator to ensure schema exists before running a query."""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                if "no such table" in str(e).lower():
                    self._init_db()
                    return func(*args, **kwargs)
                raise
        return wrapper
    

    def _migrate_db(self):
        """Surgical Schema Upgrade: Adds missing columns to existing databases."""
        columns_to_add = [
            ("posted_date", "TEXT DEFAULT ''"),
            ("hiring_manager", "TEXT DEFAULT ''"),
            ("match_reason", "TEXT DEFAULT ''")
        ]
        
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("PRAGMA table_info(applications)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            
            for col_name, col_def in columns_to_add:
                if col_name not in existing_columns:
                    try:
                        print(f"[System] Database Upgrade: Adding missing column '{col_name}'...")
                        conn.execute(f"ALTER TABLE applications ADD COLUMN {col_name} {col_def}")
                    except Exception as e:
                        print(f"[Warning] Migration failed for {col_name}: {e}")
            conn.commit()

    def _init_db(self):

        """Initialize the database schema."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_title TEXT NOT NULL,
                    company TEXT DEFAULT '',
                    location TEXT DEFAULT '',
                    description TEXT DEFAULT '',
                    apply_url TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    status TEXT DEFAULT 'new',
                    resume_path TEXT DEFAULT '',
                    cover_letter_path TEXT DEFAULT '',
                    date_found TEXT DEFAULT '',
                    date_applied TEXT DEFAULT '',
                    notes TEXT DEFAULT '',
                    match_score INTEGER DEFAULT 0,
                    match_reason TEXT DEFAULT '',
                    posted_date TEXT DEFAULT '',
                    hiring_manager TEXT DEFAULT ''
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS outreach_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    type TEXT, -- LinkedIn, Email, Call
                    contact_name TEXT,
                    message_snippet TEXT,
                    status TEXT DEFAULT 'sent', -- sent, replied
                    created_at TEXT,
                    FOREIGN KEY (application_id) REFERENCES applications (id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS failure_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER NOT NULL,
                    failed_at_step INTEGER,
                    reason TEXT,
                    created_at TEXT,
                    FOREIGN KEY (application_id) REFERENCES applications (id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS crm_outreach (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    application_id INTEGER,
                    sender TEXT,
                    subject TEXT,
                    body TEXT,
                    sentiment TEXT,
                    date_received TEXT,
                    action_taken TEXT DEFAULT 'none',
                    FOREIGN KEY (application_id) REFERENCES applications (id)
                )
            """)
            conn.commit()

    def _row_to_application(self, row: tuple) -> Application:
        """Convert a database row to an Application object."""
        return Application(
            id=row[0],
            job_title=row[1],
            company=row[2],
            location=row[3],
            description=row[4],
            apply_url=row[5],
            source=row[6],
            status=row[7],
            resume_path=row[8],
            cover_letter_path=row[9],
            date_found=row[10],
            date_applied=row[11],
            notes=row[12],
            match_score=row[13],
            match_reason=row[14] if len(row) > 14 else ""
        )

    def add(
        self,
        job_title: str,
        company: str = "",
        location: str = "",
        description: str = "",
        apply_url: str = "",
        source: str = "",
        status: str = "new",
        resume_path: str = "",
        cover_letter_path: str = "",
        notes: str = "",
        match_score: int = 0,
        match_reason: str = "",
    ) -> int:
        """
        Add a new application to the tracker.
        Returns the new application ID.
        """
        # Phase 24.1: Ensure schema before adding
        try:
            return self._add_logic(job_title, company, location, description, apply_url, source, status, resume_path, cover_letter_path, notes, match_score, match_reason)
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                self._init_db()
                return self._add_logic(job_title, company, location, description, apply_url, source, status, resume_path, cover_letter_path, notes, match_score, match_reason)
            raise

    def _add_logic(self, job_title, company, location, description, apply_url, source, status, resume_path, cover_letter_path, notes, match_score, match_reason=""):
        # 1. Exact URL match (Strongest)
        if apply_url:
            existing = self.find_by_url(apply_url)
            if existing: return existing.id

        # 2. Fuzzy match: Company + Title (Prevents re-applying to same role on different sites)
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT id FROM applications WHERE LOWER(job_title) = ? AND LOWER(company) = ?",
                (job_title.lower(), company.lower())
            )
            row = cursor.fetchone()
            if row:
                return row[0]


        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO applications 
                (job_title, company, location, description, apply_url, source,
                 status, resume_path, cover_letter_path, date_found, date_applied, notes, match_score, match_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_title, company, location, description, apply_url, source,
                    status, resume_path, cover_letter_path, now,
                    now if status == "applied" else "", notes, match_score, match_reason
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def update_status(self, app_id: int, status: str, notes: str = ""):
        """Update the status of an application."""
        if status not in self.STATUSES:
            raise ValueError(f"Invalid status: '{status}'. Choose from: {self.STATUSES}")

        updates = {"status": status}
        if status == "applied":
            updates["date_applied"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values())

        if notes:
            set_clause += ", notes = ?"
            values.append(notes)

        values.append(app_id)

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(f"UPDATE applications SET {set_clause} WHERE id = ?", values)
            conn.commit()

    def update_documents(self, app_id: int, resume_path: str = "", cover_letter_path: str = ""):
        """Update document paths for an application."""
        updates = {}
        if resume_path:
            updates["resume_path"] = resume_path
        if cover_letter_path:
            updates["cover_letter_path"] = cover_letter_path

        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [app_id]

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute(f"UPDATE applications SET {set_clause} WHERE id = ?", values)
            conn.commit()

    def log_failure_details(self, app_id: int, step: int, reason: str):
        """Log granular failure details for debug/retry purposes (Phase 28)."""
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                conn.execute('''
                    INSERT INTO failure_logs (application_id, failed_at_step, reason, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (app_id, step, reason, datetime.now().isoformat()))
                conn.commit()
        except Exception: pass

    def log_outreach(self, app_id: Optional[int], sender: str, subject: str, body: str, sentiment: str = "neutral"):
        """Log a detected recruiter message into the CRM."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO crm_outreach (application_id, sender, subject, body, sentiment, date_received)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (app_id, sender, subject, body, sentiment, now))
            conn.commit()

    def get_outreach(self) -> list[dict]:
        """Get all recruiter outreach messages for the CRM dashboard."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM crm_outreach ORDER BY date_received DESC")
            return [dict(row) for row in cursor.fetchall()]

    def get(self, app_id: int) -> Optional[Application]:
        """Get a single application by ID."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,))
            row = cursor.fetchone()
            return self._row_to_application(row) if row else None

    def get_all(self) -> list[Application]:
        """Get all tracked applications."""
        try:
            return self._get_all_logic()
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                self._init_db()
                return self._get_all_logic()
            raise

    def _get_all_logic(self) -> list[Application]:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute("SELECT * FROM applications ORDER BY date_found DESC")
            return [self._row_to_application(row) for row in cursor.fetchall()]


    def get_by_status(self, status: str) -> list[Application]:
        """Get applications filtered by status."""
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY date_found DESC",
                (status,),
            )
            return [self._row_to_application(row) for row in cursor.fetchall()]

    def find_by_url(self, url: str) -> Optional[Application]:
        """Find an application by its apply URL."""
        try:
            return self._find_by_url_logic(url)
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                self._init_db()
                return self._find_by_url_logic(url)
            raise

    def _find_by_url_logic(self, url: str) -> Optional[Application]:
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                "SELECT * FROM applications WHERE apply_url = ?", (url,)
            )
            row = cursor.fetchone()
            return self._row_to_application(row) if row else None

    def get_pending_reviews(self) -> list[dict]:
        """Get all jobs that are tracked but not yet applied or skipped."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM applications WHERE status = 'new' ORDER BY match_score DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> dict:
        """Alias for get_analytics to ensure GUI/CLI compatibility."""
        return self.get_analytics()


    def delete(self, app_id: int):
        """Surgical Termination: Purge an application and its associated tactical logs."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # Clean up child tables first
            conn.execute("DELETE FROM failure_logs WHERE application_id = ?", (app_id,))
            conn.execute("DELETE FROM crm_outreach WHERE application_id = ?", (app_id,))
            # Terminate master record
            conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            conn.commit()
            print(f"[System] Mission target {app_id} successfully terminated.")

    def get_analytics(self) -> dict:
        """Get detailed application analytics."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # 1. Platform Breakdown
            platforms = conn.execute(
                "SELECT source, COUNT(*) FROM applications GROUP BY source"
            ).fetchall()
            platform_stats = {row[0]: row[1] for row in platforms}

            # 2. Success Rate (applied vs total)
            applied = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE status = 'applied'"
            ).fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            success_rate = (applied / total * 100) if total > 0 else 0

            # 3. Status Breakdown
            statuses = conn.execute(
                "SELECT status, COUNT(*) FROM applications GROUP BY status"
            ).fetchall()
            status_stats = {row[0]: row[1] for row in statuses}

            # 4. Recent activity (last 7 days)
            last_7_days = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE date_found >= date('now', '-7 days')"
            ).fetchone()[0]

            # 5. Pipeline Stages for Funnel
            interviews = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE status = 'interview'"
            ).fetchone()[0]
            offers = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE status = 'offer'"
            ).fetchone()[0]

            return {
                "total": total,
                "applied": applied,
                "interviews": interviews,
                "offers": offers,
                "success_rate": round(success_rate, 1),
                "platforms": platform_stats,
                "statuses": status_stats,
                "recent_7_days": last_7_days,
                "platform_roi": self._calculate_platform_roi(),
                "ghost_count": self._count_ghost_jobs()
            }

    def _calculate_platform_roi(self) -> dict:
        """Calculate success rate per platform."""
        with sqlite3.connect(str(self.db_path)) as conn:
            query = """
                SELECT source, 
                       COUNT(*) as total,
                       SUM(CASE WHEN status='applied' THEN 1 ELSE 0 END) as applied,
                       SUM(CASE WHEN status='interview' THEN 1 ELSE 0 END) as interviews
                FROM applications
                GROUP BY source
            """
            rows = conn.execute(query).fetchall()
            return {row[0]: {"total": row[1], "applied": row[2], "interviews": row[3]} for row in rows}

    def _count_ghost_jobs(self) -> int:
        """Count jobs that are likely stale (posted > 60 days ago)."""
        with sqlite3.connect(str(self.db_path)) as conn:
            # We assume ISO format or similar for posted_date
            return conn.execute(
                "SELECT COUNT(*) FROM applications WHERE posted_date < date('now', '-60 days')"
            ).fetchone()[0]

    def add_outreach_log(self, application_id: int, log_type: str, contact_name: str, message: str):
        """Record a strategic outreach event."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                INSERT INTO outreach_logs (application_id, type, contact_name, message_snippet, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (application_id, log_type, contact_name, message, now))
            conn.commit()

    def get_outreach_logs(self, application_id: int) -> list[dict]:
        """Retrieve full networking history for a mission target."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM outreach_logs WHERE application_id = ? ORDER BY created_at DESC",
                (application_id,)
            ).fetchall()
            return [dict(row) for row in rows]


if __name__ == "__main__":
    import tempfile
    import os
    # Test with a temporary database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        temp_db = Path(tf.name)
    
    tracker = Tracker(temp_db)

    # Add test applications
    id1 = tracker.add(
        job_title="Senior Python Developer",
        company="Tech Corp",
        location="Remote",
        apply_url="https://indeed.com/job/123",
        source="Indeed",
        match_score=95,
    )
    print(f"✓ Added application ID: {id1}")

    id2 = tracker.add(
        job_title="Full Stack Engineer",
        company="StartupXYZ",
        location="New York, NY",
        apply_url="https://linkedin.com/job/456",
        source="LinkedIn",
        match_score=82,
    )
    print(f"✓ Added application ID: {id2}")

    # Test duplicate detection
    dup_id = tracker.add(
        job_title="Senior Python Developer",
        apply_url="https://indeed.com/job/123",
    )
    print(f"✓ Duplicate detected, returned existing ID: {dup_id}")

    # Update status
    tracker.update_status(id1, "applied", "Submitted via auto-apply")
    print(f"✓ Updated status for ID {id1}")

    # Get all
    all_apps = tracker.get_all()
    print(f"\nAll applications ({len(all_apps)}):")
    for app in all_apps:
        print(f"  [{app.id}] {app.job_title} @ {app.company} — {app.status}")

    # Analytics
    analytics = tracker.get_analytics()
    print(f"\nAnalytics: {analytics}")

    # Cleanup
    temp_db.unlink()
    print("✓ Test complete!")
