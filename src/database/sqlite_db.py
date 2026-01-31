"""SQLite database for persisting leads locally."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from ..utils.models import Lead, LeadSource
from ..utils.logger import setup_logger

logger = setup_logger("database")

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "leads.db"


class LeadDatabase:
    """SQLite database for storing and managing leads locally."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to data/leads.db
        """
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self):
        """Create database tables if they don't exist."""
        with self._get_connection() as conn:
            conn.executescript("""
                -- Main leads table
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    username TEXT,
                    email TEXT,
                    name TEXT,
                    company TEXT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    url TEXT NOT NULL,
                    subreddit TEXT,
                    ai_score REAL,
                    ai_reasoning TEXT,
                    is_qualified INTEGER DEFAULT 0,
                    sent_to_crm INTEGER DEFAULT 0,
                    hubspot_id TEXT,
                    found_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Keywords matched (many-to-many)
                CREATE TABLE IF NOT EXISTS lead_keywords (
                    lead_id TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    PRIMARY KEY (lead_id, keyword),
                    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
                );

                -- Scraping runs history
                CREATE TABLE IF NOT EXISTS scrape_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    total_found INTEGER DEFAULT 0,
                    qualified_count INTEGER DEFAULT 0,
                    sources TEXT
                );

                -- Indexes for faster queries
                CREATE INDEX IF NOT EXISTS idx_leads_source ON leads(source);
                CREATE INDEX IF NOT EXISTS idx_leads_qualified ON leads(is_qualified);
                CREATE INDEX IF NOT EXISTS idx_leads_sent_crm ON leads(sent_to_crm);
                CREATE INDEX IF NOT EXISTS idx_leads_found_at ON leads(found_at);
            """)
            logger.info(f"Database initialized at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper cleanup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    # ==================== SAVE OPERATIONS ====================

    def save_lead(self, lead: Lead) -> bool:
        """Save a single lead to the database.

        Args:
            lead: Lead object to save

        Returns:
            True if saved (new), False if already existed
        """
        with self._get_connection() as conn:
            # Check if lead already exists
            existing = conn.execute(
                "SELECT id FROM leads WHERE id = ?", (lead.id,)
            ).fetchone()

            if existing:
                logger.debug(f"Lead {lead.id[:8]} already exists, skipping")
                return False

            # Insert lead
            now = datetime.utcnow().isoformat()
            conn.execute("""
                INSERT INTO leads (
                    id, source, username, email, name, company,
                    title, content, url, subreddit,
                    ai_score, ai_reasoning, is_qualified,
                    sent_to_crm, hubspot_id, found_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead.id,
                lead.source.value,
                lead.username,
                lead.email,
                lead.name,
                lead.company,
                lead.title,
                lead.content,
                lead.url,
                lead.subreddit,
                lead.ai_score,
                lead.ai_reasoning,
                1 if lead.is_qualified else 0,
                1 if lead.sent_to_crm else 0,
                lead.hubspot_id,
                lead.found_at.isoformat(),
                now
            ))

            # Save keywords
            for keyword in lead.keywords_matched:
                conn.execute(
                    "INSERT OR IGNORE INTO lead_keywords (lead_id, keyword) VALUES (?, ?)",
                    (lead.id, keyword)
                )

            logger.debug(f"Saved lead {lead.id[:8]}")
            return True

    def save_leads(self, leads: List[Lead]) -> Dict[str, int]:
        """Save multiple leads to the database.

        Args:
            leads: List of Lead objects

        Returns:
            Dict with counts: {'saved': X, 'duplicates': Y}
        """
        saved = 0
        duplicates = 0

        for lead in leads:
            if self.save_lead(lead):
                saved += 1
            else:
                duplicates += 1

        logger.info(f"Saved {saved} leads, {duplicates} duplicates skipped")
        return {"saved": saved, "duplicates": duplicates}

    # ==================== READ OPERATIONS ====================

    def _row_to_lead(self, row: sqlite3.Row) -> Lead:
        """Convert a database row to a Lead object."""
        # Get keywords for this lead
        with self._get_connection() as conn:
            keywords = conn.execute(
                "SELECT keyword FROM lead_keywords WHERE lead_id = ?",
                (row["id"],)
            ).fetchall()

        return Lead(
            id=row["id"],
            source=LeadSource(row["source"]),
            username=row["username"],
            email=row["email"],
            name=row["name"],
            company=row["company"],
            title=row["title"],
            content=row["content"],
            url=row["url"],
            subreddit=row["subreddit"],
            keywords_matched=[k["keyword"] for k in keywords],
            ai_score=row["ai_score"],
            ai_reasoning=row["ai_reasoning"],
            is_qualified=bool(row["is_qualified"]),
            sent_to_crm=bool(row["sent_to_crm"]),
            hubspot_id=row["hubspot_id"],
            found_at=datetime.fromisoformat(row["found_at"])
        )

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a single lead by ID."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM leads WHERE id = ?", (lead_id,)
            ).fetchone()

            if row:
                return self._row_to_lead(row)
            return None

    def get_all_leads(self, limit: int = 100, offset: int = 0) -> List[Lead]:
        """Get all leads with pagination."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM leads ORDER BY found_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()

            return [self._row_to_lead(row) for row in rows]

    def get_leads_by_source(self, source: LeadSource, limit: int = 50) -> List[Lead]:
        """Get leads filtered by source."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM leads WHERE source = ? ORDER BY found_at DESC LIMIT ?",
                (source.value, limit)
            ).fetchall()

            return [self._row_to_lead(row) for row in rows]

    def get_qualified_leads(self, limit: int = 50) -> List[Lead]:
        """Get only qualified leads."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM leads WHERE is_qualified = 1 ORDER BY ai_score DESC LIMIT ?",
                (limit,)
            ).fetchall()

            return [self._row_to_lead(row) for row in rows]

    def get_unsent_leads(self, limit: int = 50) -> List[Lead]:
        """Get qualified leads not yet sent to CRM."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM leads
                   WHERE is_qualified = 1 AND sent_to_crm = 0
                   ORDER BY ai_score DESC LIMIT ?""",
                (limit,)
            ).fetchall()

            return [self._row_to_lead(row) for row in rows]

    def search_leads(self, query: str, limit: int = 50) -> List[Lead]:
        """Search leads by title, content, company, or email."""
        with self._get_connection() as conn:
            search_term = f"%{query}%"
            rows = conn.execute(
                """SELECT * FROM leads
                   WHERE title LIKE ? OR content LIKE ? OR company LIKE ? OR email LIKE ?
                   ORDER BY found_at DESC LIMIT ?""",
                (search_term, search_term, search_term, search_term, limit)
            ).fetchall()

            return [self._row_to_lead(row) for row in rows]

    def lead_exists(self, lead_id: str) -> bool:
        """Check if a lead already exists in the database."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM leads WHERE id = ?", (lead_id,)
            ).fetchone()
            return row is not None

    def url_exists(self, url: str) -> bool:
        """Check if a lead with this URL already exists."""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM leads WHERE url = ?", (url,)
            ).fetchone()
            return row is not None

    # ==================== UPDATE OPERATIONS ====================

    def update_lead(self, lead_id: str, **kwargs) -> bool:
        """Update specific fields of a lead.

        Args:
            lead_id: ID of the lead to update
            **kwargs: Fields to update (ai_score, is_qualified, sent_to_crm, etc.)

        Returns:
            True if updated, False if lead not found
        """
        allowed_fields = {
            "ai_score", "ai_reasoning", "is_qualified", "sent_to_crm",
            "hubspot_id", "email", "name", "company"
        }

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        # Convert booleans to integers for SQLite
        for key in ["is_qualified", "sent_to_crm"]:
            if key in updates:
                updates[key] = 1 if updates[key] else 0

        updates["updated_at"] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [lead_id]

        with self._get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE leads SET {set_clause} WHERE id = ?",
                values
            )
            return cursor.rowcount > 0

    def mark_as_sent(self, lead_id: str, hubspot_id: str) -> bool:
        """Mark a lead as sent to CRM."""
        return self.update_lead(lead_id, sent_to_crm=True, hubspot_id=hubspot_id)

    def mark_leads_as_sent(self, lead_ids: List[str]) -> int:
        """Mark multiple leads as sent to CRM."""
        count = 0
        for lead_id in lead_ids:
            if self.update_lead(lead_id, sent_to_crm=True):
                count += 1
        return count

    # ==================== DELETE OPERATIONS ====================

    def delete_lead(self, lead_id: str) -> bool:
        """Delete a lead from the database."""
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            return cursor.rowcount > 0

    def delete_old_leads(self, days: int = 90) -> int:
        """Delete leads older than specified days."""
        cutoff = datetime.utcnow()
        cutoff = cutoff.replace(day=cutoff.day - days) if cutoff.day > days else cutoff

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM leads WHERE found_at < ?",
                (cutoff.isoformat(),)
            )
            deleted = cursor.rowcount
            logger.info(f"Deleted {deleted} leads older than {days} days")
            return deleted

    # ==================== STATISTICS ====================

    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._get_connection() as conn:
            stats = {}

            # Total counts
            stats["total_leads"] = conn.execute(
                "SELECT COUNT(*) FROM leads"
            ).fetchone()[0]

            stats["qualified_leads"] = conn.execute(
                "SELECT COUNT(*) FROM leads WHERE is_qualified = 1"
            ).fetchone()[0]

            stats["sent_to_crm"] = conn.execute(
                "SELECT COUNT(*) FROM leads WHERE sent_to_crm = 1"
            ).fetchone()[0]

            stats["pending_send"] = conn.execute(
                "SELECT COUNT(*) FROM leads WHERE is_qualified = 1 AND sent_to_crm = 0"
            ).fetchone()[0]

            # By source
            source_rows = conn.execute(
                "SELECT source, COUNT(*) as count FROM leads GROUP BY source"
            ).fetchall()
            stats["by_source"] = {row["source"]: row["count"] for row in source_rows}

            # Average AI score
            avg_score = conn.execute(
                "SELECT AVG(ai_score) FROM leads WHERE ai_score IS NOT NULL"
            ).fetchone()[0]
            stats["avg_ai_score"] = round(avg_score, 3) if avg_score else 0

            # Leads today
            today = datetime.utcnow().date().isoformat()
            stats["leads_today"] = conn.execute(
                "SELECT COUNT(*) FROM leads WHERE found_at >= ?",
                (today,)
            ).fetchone()[0]

            # Top keywords
            keyword_rows = conn.execute(
                """SELECT keyword, COUNT(*) as count
                   FROM lead_keywords
                   GROUP BY keyword
                   ORDER BY count DESC
                   LIMIT 10"""
            ).fetchall()
            stats["top_keywords"] = {row["keyword"]: row["count"] for row in keyword_rows}

            return stats

    # ==================== SCRAPE RUNS ====================

    def start_scrape_run(self, sources: List[str]) -> int:
        """Record the start of a scraping run."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO scrape_runs (started_at, sources) VALUES (?, ?)",
                (datetime.utcnow().isoformat(), ",".join(sources))
            )
            return cursor.lastrowid

    def complete_scrape_run(self, run_id: int, total_found: int, qualified_count: int):
        """Record the completion of a scraping run."""
        with self._get_connection() as conn:
            conn.execute(
                """UPDATE scrape_runs
                   SET completed_at = ?, total_found = ?, qualified_count = ?
                   WHERE id = ?""",
                (datetime.utcnow().isoformat(), total_found, qualified_count, run_id)
            )

    def get_recent_runs(self, limit: int = 10) -> List[Dict]:
        """Get recent scraping runs."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM scrape_runs ORDER BY started_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

            return [dict(row) for row in rows]
