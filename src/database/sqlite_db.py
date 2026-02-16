"""SQLite database for persisting leads locally."""

import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from contextlib import contextmanager

from ..utils.models import Lead, LeadSource, LeadUrgency, LeadCategory
from ..utils.logger import get_logger

logger = get_logger("database")

# Default database path
DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "data" / "leads.db"

# Columns that need migration (added after initial schema)
_MIGRATION_COLUMNS = [
    ("linkedin", "TEXT"),
    ("twitter", "TEXT"),
    ("position", "TEXT"),
    ("author", "TEXT"),
    ("employees", "TEXT"),
    ("revenue", "TEXT"),
    ("country", "TEXT"),
    ("industry", "TEXT"),
    ("pain_score", "REAL"),
    ("intent_score", "REAL"),
    ("fit_score", "REAL"),
    ("total_score", "REAL"),
    ("urgency", "TEXT"),
    ("urgency_keywords_json", "TEXT"),
    ("score_breakdown_json", "TEXT"),
    ("address", "TEXT"),
    ("review_count", "INTEGER"),
    ("business_type", "TEXT"),
    ("place_id", "TEXT"),
    ("has_pain", "INTEGER DEFAULT 0"),
    ("pain_reviews_json", "TEXT"),
    ("pain_summary", "TEXT"),
    ("lead_category", "TEXT"),
    ("has_explicit_pain", "INTEGER DEFAULT 0"),
    ("software_needs", "TEXT"),
    ("has_website", "INTEGER"),
    ("has_social_media", "INTEGER"),
    ("gemini_analysis", "TEXT"),
    ("posted_at", "TEXT"),
    ("location", "TEXT"),
    ("website", "TEXT"),
    ("rating", "REAL"),
    ("status", "TEXT DEFAULT 'new'"),
    ("notes", "TEXT"),
    ("tags_json", "TEXT"),
    ("extra_data_json", "TEXT"),
]


class LeadDatabase:
    """SQLite database for storing and managing leads locally."""

    def __init__(self, db_path=None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. Defaults to data/leads.db
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
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
                    phone TEXT,
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

            # Run column migrations for existing databases
            self._run_migrations(conn)

            logger.info(f"Database initialized at {self.db_path}")

    def _run_migrations(self, conn):
        """Add missing columns to existing databases."""
        for col_name, col_type in _MIGRATION_COLUMNS:
            try:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {col_name} {col_type}")
                logger.debug(f"Added column {col_name} to leads table")
            except sqlite3.OperationalError as e:
                if "duplicate column" not in str(e).lower():
                    logger.warning(f"Migration error for column {col_name}: {e}")

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
                    id, source, username, email, phone, name, company,
                    title, content, url, subreddit,
                    ai_score, ai_reasoning, is_qualified,
                    sent_to_crm, hubspot_id, found_at, updated_at,
                    linkedin, twitter, position, author,
                    employees, revenue, country, industry,
                    pain_score, intent_score, fit_score, total_score,
                    urgency, urgency_keywords_json, score_breakdown_json,
                    address, review_count, business_type, place_id,
                    has_pain, pain_reviews_json, pain_summary,
                    lead_category, has_explicit_pain,
                    software_needs, has_website, has_social_media, gemini_analysis,
                    posted_at, location, website, rating,
                    status, notes, tags_json, extra_data_json
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?
                )
            """, (
                lead.id,
                lead.source.value,
                lead.username,
                lead.email,
                lead.phone,
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
                now,
                # Professional & Social
                lead.linkedin,
                lead.twitter,
                lead.position,
                lead.author,
                # Company info
                lead.employees,
                lead.revenue,
                lead.country,
                lead.industry,
                # Scoring
                lead.pain_score,
                lead.intent_score,
                lead.fit_score,
                lead.total_score,
                lead.urgency.value if lead.urgency else None,
                json.dumps(lead.urgency_keywords_matched) if lead.urgency_keywords_matched else None,
                json.dumps(lead.score_breakdown) if lead.score_breakdown else None,
                # Google Maps
                lead.address,
                lead.review_count,
                lead.business_type,
                lead.place_id,
                # Pain detection
                1 if lead.has_pain else 0,
                json.dumps(lead.pain_reviews) if lead.pain_reviews else None,
                lead.pain_summary,
                # AI category
                lead.lead_category.value if lead.lead_category else None,
                1 if lead.has_explicit_pain else 0,
                # Gemini
                lead.software_needs,
                1 if lead.has_website else (0 if lead.has_website is not None else None),
                1 if lead.has_social_media else (0 if lead.has_social_media is not None else None),
                lead.gemini_analysis,
                # Tracking
                lead.posted_at.isoformat() if lead.posted_at else None,
                lead.location,
                lead.website,
                lead.rating,
                # CRM
                lead.status,
                lead.notes,
                json.dumps(lead.tags) if lead.tags else None,
                json.dumps(lead.extra_data) if lead.extra_data else None,
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

    def _safe_get(self, row: sqlite3.Row, key: str, default=None):
        """Safely get a value from a row, returning default if column doesn't exist."""
        try:
            if key in row.keys():
                return row[key]
        except Exception:
            pass
        return default

    def _row_to_lead(self, row: sqlite3.Row) -> Lead:
        """Convert a database row to a Lead object."""
        # Get keywords for this lead
        with self._get_connection() as conn:
            keywords = conn.execute(
                "SELECT keyword FROM lead_keywords WHERE lead_id = ?",
                (row["id"],)
            ).fetchall()

        # Parse JSON fields safely
        urgency_keywords = []
        raw = self._safe_get(row, "urgency_keywords_json")
        if raw:
            try:
                urgency_keywords = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass

        score_breakdown = None
        raw = self._safe_get(row, "score_breakdown_json")
        if raw:
            try:
                score_breakdown = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass

        pain_reviews = []
        raw = self._safe_get(row, "pain_reviews_json")
        if raw:
            try:
                pain_reviews = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass

        tags = []
        raw = self._safe_get(row, "tags_json")
        if raw:
            try:
                tags = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass

        extra_data = {}
        raw = self._safe_get(row, "extra_data_json")
        if raw:
            try:
                extra_data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                pass

        # Parse urgency enum
        urgency = None
        raw_urgency = self._safe_get(row, "urgency")
        if raw_urgency:
            try:
                urgency = LeadUrgency(raw_urgency)
            except ValueError:
                pass

        # Parse lead_category enum
        lead_category = None
        raw_cat = self._safe_get(row, "lead_category")
        if raw_cat:
            try:
                lead_category = LeadCategory(raw_cat)
            except ValueError:
                pass

        # Parse posted_at datetime
        posted_at = None
        raw_posted = self._safe_get(row, "posted_at")
        if raw_posted:
            try:
                posted_at = datetime.fromisoformat(raw_posted)
            except (ValueError, TypeError):
                pass

        # Parse has_website / has_social_media (nullable booleans)
        has_website_raw = self._safe_get(row, "has_website")
        has_website = bool(has_website_raw) if has_website_raw is not None else None

        has_social_raw = self._safe_get(row, "has_social_media")
        has_social_media = bool(has_social_raw) if has_social_raw is not None else None

        return Lead(
            id=row["id"],
            source=LeadSource(row["source"]),
            username=row["username"],
            email=row["email"],
            phone=self._safe_get(row, "phone"),
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
            found_at=datetime.fromisoformat(row["found_at"]),
            # Professional & Social
            linkedin=self._safe_get(row, "linkedin"),
            twitter=self._safe_get(row, "twitter"),
            position=self._safe_get(row, "position"),
            author=self._safe_get(row, "author"),
            # Company info
            employees=self._safe_get(row, "employees"),
            revenue=self._safe_get(row, "revenue"),
            country=self._safe_get(row, "country"),
            industry=self._safe_get(row, "industry"),
            # Scoring
            pain_score=self._safe_get(row, "pain_score"),
            intent_score=self._safe_get(row, "intent_score"),
            fit_score=self._safe_get(row, "fit_score"),
            total_score=self._safe_get(row, "total_score"),
            urgency=urgency,
            urgency_keywords_matched=urgency_keywords,
            score_breakdown=score_breakdown,
            # Google Maps
            address=self._safe_get(row, "address"),
            review_count=self._safe_get(row, "review_count"),
            business_type=self._safe_get(row, "business_type"),
            place_id=self._safe_get(row, "place_id"),
            # Pain detection
            has_pain=bool(self._safe_get(row, "has_pain", 0)),
            pain_reviews=pain_reviews,
            pain_summary=self._safe_get(row, "pain_summary"),
            # AI
            lead_category=lead_category,
            has_explicit_pain=bool(self._safe_get(row, "has_explicit_pain", 0)),
            # Gemini
            software_needs=self._safe_get(row, "software_needs"),
            has_website=has_website,
            has_social_media=has_social_media,
            gemini_analysis=self._safe_get(row, "gemini_analysis"),
            # Tracking
            posted_at=posted_at,
            location=self._safe_get(row, "location"),
            website=self._safe_get(row, "website"),
            rating=self._safe_get(row, "rating"),
            # CRM
            status=self._safe_get(row, "status", "new"),
            notes=self._safe_get(row, "notes"),
            tags=tags,
            extra_data=extra_data,
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
            "hubspot_id", "email", "name", "company", "phone",
            "pain_score", "intent_score", "fit_score", "total_score",
            "lead_category", "has_explicit_pain", "status", "notes",
            "software_needs", "has_website", "has_social_media", "gemini_analysis",
        }

        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        if not updates:
            return False

        # Convert booleans to integers for SQLite
        for key in ["is_qualified", "sent_to_crm", "has_explicit_pain", "has_website", "has_social_media"]:
            if key in updates:
                updates[key] = 1 if updates[key] else 0

        # Convert enums to values
        if "lead_category" in updates and updates["lead_category"] is not None:
            if hasattr(updates["lead_category"], "value"):
                updates["lead_category"] = updates["lead_category"].value

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

    # ==================== EXPORT OPERATIONS ====================

    def export_to_csv(self, filepath: Optional[Path] = None, qualified_only: bool = False) -> Path:
        """Export leads to CSV file.

        Args:
            filepath: Output file path. Defaults to data/leads_export_TIMESTAMP.csv
            qualified_only: If True, only export qualified leads

        Returns:
            Path to the exported CSV file
        """
        if filepath is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filepath = self.db_path.parent / f"leads_export_{timestamp}.csv"

        with self._get_connection() as conn:
            # Get all leads with keywords
            query = "SELECT * FROM leads"
            if qualified_only:
                query += " WHERE is_qualified = 1"
            query += " ORDER BY found_at DESC"

            rows = conn.execute(query).fetchall()

            # Get keywords for each lead
            leads_data = []
            for row in rows:
                keywords = conn.execute(
                    "SELECT keyword FROM lead_keywords WHERE lead_id = ?",
                    (row["id"],)
                ).fetchall()

                lead_dict = dict(row)
                lead_dict["keywords"] = ", ".join(k["keyword"] for k in keywords)
                leads_data.append(lead_dict)

        # Write to CSV
        if leads_data:
            fieldnames = [
                "id", "source", "title", "url", "email", "phone", "company",
                "username", "name", "keywords", "ai_score", "is_qualified",
                "sent_to_crm", "hubspot_id", "found_at", "subreddit",
                "industry", "pain_score", "intent_score", "fit_score", "total_score",
                "lead_category", "location", "website", "rating", "status", "notes",
            ]

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(leads_data)

            logger.info(f"Exported {len(leads_data)} leads to {filepath}")
        else:
            # Create empty file with headers
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["id", "source", "title", "url", "email", "phone",
                                "company", "username", "name", "keywords"])
            logger.info(f"No leads to export, created empty CSV at {filepath}")

        return filepath
