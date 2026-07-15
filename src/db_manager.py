"""Database manager for the Arabic Medical Glossary using SQLite with FTS5."""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import DB_PATH

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages all SQLite database operations for the glossary."""

    def __init__(self, db_path: Optional[str | Path] = None) -> None:
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: sqlite3.Connection = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def _create_tables(self) -> None:
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS terms (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                english         TEXT NOT NULL,
                arabic          TEXT NOT NULL,
                category        TEXT DEFAULT '',
                source          TEXT DEFAULT '',
                confidence      REAL DEFAULT 0.5,
                type            TEXT DEFAULT 'term',
                section         TEXT DEFAULT '',
                hash            TEXT NOT NULL UNIQUE,
                verified        TEXT DEFAULT 'unverified',
                usage_count     INTEGER DEFAULT 0,
                priority        INTEGER DEFAULT 0,
                medical_specialty TEXT DEFAULT '',
                term_complexity TEXT DEFAULT '',
                region          TEXT DEFAULT 'global',
                validation_status TEXT DEFAULT 'unverified',
                notes           TEXT DEFAULT '',
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT DEFAULT (datetime('now')),
                UNIQUE(english, arabic, source)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                name          TEXT PRIMARY KEY,
                description   TEXT DEFAULT '',
                url           TEXT DEFAULT '',
                quality_score REAL DEFAULT 0.5,
                term_count    INTEGER DEFAULT 0,
                last_updated  TEXT DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS change_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                term_id    INTEGER NOT NULL REFERENCES terms(id) ON DELETE CASCADE,
                action     TEXT NOT NULL,
                field      TEXT DEFAULT '',
                old_value  TEXT DEFAULT '',
                new_value  TEXT DEFAULT '',
                timestamp  TEXT DEFAULT (datetime('now'))
            )
        """)

        # FTS5 virtual table
        cur.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS terms_fts USING fts5(
                english, arabic, category, source, section,
                content='terms', content_rowid='id'
            )
        """)

        # Triggers to keep FTS in sync
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS terms_fts_ai AFTER INSERT ON terms BEGIN
                INSERT INTO terms_fts(rowid, english, arabic, category, source, section)
                VALUES (new.id, new.english, new.arabic, new.category, new.source, new.section);
            END
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS terms_fts_ad AFTER DELETE ON terms BEGIN
                INSERT INTO terms_fts(terms_fts, rowid, english, arabic, category, source, section)
                VALUES ('delete', old.id, old.english, old.arabic, old.category, old.source, old.section);
            END
        """)
        cur.execute("""
            CREATE TRIGGER IF NOT EXISTS terms_fts_au AFTER UPDATE ON terms BEGIN
                INSERT INTO terms_fts(terms_fts, rowid, english, arabic, category, source, section)
                VALUES ('delete', old.id, old.english, old.arabic, old.category, old.source, old.section);
                INSERT INTO terms_fts(rowid, english, arabic, category, source, section)
                VALUES (new.id, new.english, new.arabic, new.category, new.source, new.section);
            END
        """)

        # Indexes
        idx_defs = [
            "CREATE INDEX IF NOT EXISTS idx_terms_english ON terms(english)",
            "CREATE INDEX IF NOT EXISTS idx_terms_arabic ON terms(arabic)",
            "CREATE INDEX IF NOT EXISTS idx_terms_source ON terms(source)",
            "CREATE INDEX IF NOT EXISTS idx_terms_category ON terms(category)",
            "CREATE INDEX IF NOT EXISTS idx_terms_confidence ON terms(confidence)",
            "CREATE INDEX IF NOT EXISTS idx_terms_type ON terms(type)",
            "CREATE INDEX IF NOT EXISTS idx_terms_hash ON terms(hash)",
        ]
        for idx in idx_defs:
            cur.execute(idx)

        self.conn.commit()

    # ------------------------------------------------------------------
    # Insert / Bulk
    # ------------------------------------------------------------------
    def add_term(self, english: str, arabic: str, **kwargs: Any) -> int:
        """Insert a single term and return its id. Raises on duplicate."""
        now = datetime.now(timezone.utc).isoformat()
        cur = self.conn.execute(
            """INSERT INTO terms (english, arabic, category, source, confidence,
               type, section, hash, verified, usage_count, priority,
               medical_specialty, term_complexity, region, validation_status,
               notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                english, arabic,
                kwargs.get("category", ""),
                kwargs.get("source", ""),
                kwargs.get("confidence", 0.5),
                kwargs.get("type", "term"),
                kwargs.get("section", ""),
                kwargs.get("hash", ""),
                kwargs.get("verified", "unverified"),
                kwargs.get("usage_count", 0),
                kwargs.get("priority", 0),
                kwargs.get("medical_specialty", ""),
                kwargs.get("term_complexity", ""),
                kwargs.get("region", "global"),
                kwargs.get("validation_status", "unverified"),
                kwargs.get("notes", ""),
                now, now,
            ),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def add_terms_bulk(self, terms_list: list[dict]) -> int:
        """Bulk-insert terms. Returns number inserted."""
        now = datetime.now(timezone.utc).isoformat()
        rows = []
        for t in terms_list:
            rows.append((
                t.get("english", ""),
                t.get("arabic", ""),
                t.get("category", ""),
                t.get("source", ""),
                t.get("confidence", 0.5),
                t.get("type", "term"),
                t.get("section", ""),
                t.get("hash", ""),
                t.get("verified", "unverified"),
                t.get("usage_count", 0),
                t.get("priority", 0),
                t.get("medical_specialty", ""),
                t.get("term_complexity", ""),
                t.get("region", "global"),
                t.get("validation_status", "unverified"),
                t.get("notes", ""),
                now, now,
            ))
        cur = self.conn.executemany(
            """INSERT OR IGNORE INTO terms (english, arabic, category, source,
               confidence, type, section, hash, verified, usage_count, priority,
               medical_specialty, term_complexity, region, validation_status,
               notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
        self.conn.commit()
        return cur.rowcount

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------
    def get_term(self, term_id: int) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM terms WHERE id=?", (term_id,)).fetchone()
        return dict(row) if row else None

    def search_by_english(self, query: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM terms WHERE english LIKE ? LIMIT ?", (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def search_by_arabic(self, query: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM terms WHERE arabic LIKE ? LIMIT ?", (f"%{query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]

    def search(
        self,
        query: str = "",
        category: str = "",
        source: str = "",
        type: str = "",
        limit: int = 50,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            clauses.append("(english LIKE ? OR arabic LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if category:
            clauses.append("category = ?")
            params.append(category)
        if source:
            clauses.append("source = ?")
            params.append(source)
        if type:
            clauses.append("type = ?")
            params.append(type)

        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        params.append(limit)
        rows = self.conn.execute(
            f"SELECT * FROM terms{where} LIMIT ?", params
        ).fetchall()
        return [dict(r) for r in rows]

    def fulltext_search(
        self, query: str, limit: int = 50, category: str = ""
    ) -> list[dict]:
        """FTS5 search returning terms with snippet-highlighted matches."""
        if category:
            rows = self.conn.execute(
                """SELECT t.*, snippet(terms_fts, 1, '>>>', '<<<', '...', 32) as snippet
                   FROM terms_fts f JOIN terms t ON t.id = f.rowid
                   WHERE terms_fts MATCH ? AND t.category = ?
                   LIMIT ?""",
                (query, category, limit),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT t.*, snippet(terms_fts, 1, '>>>', '<<<', '...', 32) as snippet
                   FROM terms_fts f JOIN terms t ON t.id = f.rowid
                   WHERE terms_fts MATCH ?
                   LIMIT ?""",
                (query, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Update / Delete
    # ------------------------------------------------------------------
    def update_term(self, term_id: int, **kwargs: Any) -> bool:
        if not kwargs:
            return False
        existing = self.get_term(term_id)
        if not existing:
            return False
        now = datetime.now(timezone.utc).isoformat()
        set_parts: list[str] = []
        values: list[Any] = []
        for field, new_val in kwargs.items():
            if field not in existing:
                continue
            old_val = existing[field]
            if old_val != new_val:
                set_parts.append(f"{field} = ?")
                values.append(new_val)
                self.conn.execute(
                    "INSERT INTO change_log (term_id, action, field, old_value, new_value, timestamp) VALUES (?,?,?,?,?,?)",
                    (term_id, "update", field, str(old_val), str(new_val), now),
                )
        if not set_parts:
            return False
        set_parts.append("updated_at = ?")
        values.append(now)
        values.append(term_id)
        self.conn.execute(
            f"UPDATE terms SET {', '.join(set_parts)} WHERE id = ?", values
        )
        self.conn.commit()
        return True

    def delete_term(self, term_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM terms WHERE id=?", (term_id,))
        self.conn.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------
    def get_all_sources(self) -> list[dict]:
        rows = self.conn.execute("SELECT * FROM sources ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def add_source(
        self, name: str, description: str = "", url: str = "", quality_score: float = 0.5
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO sources (name, description, url, quality_score, last_updated) VALUES (?,?,?,?,?)",
            (name, description, url, quality_score, now),
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Aggregation helpers
    # ------------------------------------------------------------------
    def get_terms_by_source(self, source: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM terms WHERE source = ? ORDER BY english", (source,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_terms_by_category(self, category: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM terms WHERE category = ? ORDER BY english", (category,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_total_count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) as c FROM terms").fetchone()
        return row["c"] if row else 0  # type: ignore[index]

    def get_random_terms(self, n: int = 10) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM terms ORDER BY RANDOM() LIMIT ?", (n,)
        ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # History & verification
    # ------------------------------------------------------------------
    def get_term_history(self, term_id: int) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM change_log WHERE term_id=? ORDER BY timestamp DESC", (term_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def verify_term(self, term_id: int, status: str = "verified") -> bool:
        return self.update_term(term_id, verified=status, validation_status=status)

    def increment_usage(self, term_id: int) -> None:
        self.conn.execute(
            "UPDATE terms SET usage_count = usage_count + 1 WHERE id=?", (term_id,)
        )
        self.conn.commit()

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    def close(self) -> None:
        if self.conn:
            self.conn.close()
            self.conn = None  # type: ignore[assignment]