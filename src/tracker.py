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


class Tracker:
    """SQLite-backed job application tracker."""

    STATUSES = ["new", "applied", "interview", "rejected", "offer", "manual_apply_needed", "skipped", "error"]

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or config.DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

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
                    match_score INTEGER DEFAULT 0
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
    ) -> int:
        """
        Add a new application to the tracker.
        Returns the new application ID.
        """
        # Phase 24.1: Ensure schema before adding
        try:
            return self._add_logic(job_title, company, location, description, apply_url, source, status, resume_path, cover_letter_path, notes, match_score)
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower():
                self._init_db()
                return self._add_logic(job_title, company, location, description, apply_url, source, status, resume_path, cover_letter_path, notes, match_score)
            raise

    def _add_logic(self, job_title, company, location, description, apply_url, source, status, resume_path, cover_letter_path, notes, match_score):
        # Check for duplicates by URL (silently return existing ID)
        if apply_url:
            existing = self.find_by_url(apply_url)
            if existing: return existing.id


        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.execute(
                """
                INSERT INTO applications 
                (job_title, company, location, description, apply_url, source,
                 status, resume_path, cover_letter_path, date_found, date_applied, notes, match_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_title, company, location, description, apply_url, source,
                    status, resume_path, cover_letter_path, now,
                    now if status == "applied" else "", notes, match_score,
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


    def delete(self, app_id: int):
        """Delete an application."""
        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("DELETE FROM applications WHERE id = ?", (app_id,))
            conn.commit()

            return {"total": total, "by_status": by_status}

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

            return {
                "total": total,
                "applied": applied,
                "success_rate": round(success_rate, 1),
                "platforms": platform_stats,
                "statuses": status_stats,
                "recent_7_days": last_7_days,
            }


if __name__ == "__main__":
    import tempfile
    # Test with a temporary database
    test_db = Path(tempfile.mktemp(suffix=".db"))
    print(f"Testing tracker with: {test_db}")

    tracker = Tracker(test_db)

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
    test_db.unlink()
    print("✓ Test complete!")
