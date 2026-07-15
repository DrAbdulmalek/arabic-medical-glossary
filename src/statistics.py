"""Statistics generation for the Arabic Medical Glossary."""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .config import (
    HIGH_CONFIDENCE_THRESHOLD,
    MEDICAL_SPECIALTIES,
    VALIDATION_STATUSES,
)

logger = logging.getLogger(__name__)


class StatisticsGenerator:
    """Generate statistics and reports about the glossary database."""

    def __init__(self, db_manager: Any) -> None:
        self.db = db_manager

    def _query(self, sql: str, params: Any = None) -> list[dict]:
        if params is None:
            params = ()
        rows = self.db.conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    def get_overview(self) -> dict[str, Any]:
        total = self.db.get_total_count()
        sources = self.db.get_all_sources()
        return {
            "total_terms": total,
            "total_sources": len(sources),
            "database_size_mb": round(
                self.db.db_path.stat().st_size / (1024 * 1024), 2
            )
            if self.db.db_path.exists()
            else 0,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def get_source_statistics(self) -> list[dict]:
        rows = self._query(
            "SELECT source, COUNT(*) as count, AVG(confidence) as avg_confidence "
            "FROM terms GROUP BY source ORDER BY count DESC"
        )
        return rows

    def get_category_statistics(self) -> list[dict]:
        rows = self._query(
            "SELECT category, COUNT(*) as count FROM terms "
            "WHERE category IS NOT NULL AND category != '' "
            "GROUP BY category ORDER BY count DESC"
        )
        return rows

    def get_type_distribution(self) -> list[dict]:
        rows = self._query(
            "SELECT type, COUNT(*) as count FROM terms "
            "GROUP BY type ORDER BY count DESC"
        )
        return rows

    def get_confidence_distribution(self) -> list[dict]:
        rows = self._query(
            "SELECT CASE "
            "  WHEN confidence >= 0.9 THEN 'high (>=0.9)' "
            "  WHEN confidence >= 0.7 THEN 'medium (0.7-0.9)' "
            "  WHEN confidence >= 0.5 THEN 'low (0.5-0.7)' "
            "  ELSE 'very_low (<0.5)' "
            "END as range, COUNT(*) as count, ROUND(AVG(confidence), 3) as avg_conf "
            "FROM terms GROUP BY range ORDER BY avg_conf DESC"
        )
        return rows

    def get_validation_statistics(self) -> list[dict]:
        rows = self._query(
            "SELECT validation_status, COUNT(*) as count FROM terms "
            "GROUP BY validation_status ORDER BY count DESC"
        )
        return rows

    def get_growth_statistics(self) -> dict[str, Any]:
        rows = self._query(
            "SELECT DATE(created_at) as date, COUNT(*) as count "
            "FROM terms GROUP BY DATE(created_at) ORDER BY date DESC LIMIT 30"
        )
        return {"recent_daily_additions": rows}

    def get_specialty_coverage(self) -> list[dict]:
        rows = self._query(
            "SELECT medical_specialty, COUNT(*) as count FROM terms "
            "WHERE medical_specialty IS NOT NULL AND medical_specialty != '' "
            "GROUP BY medical_specialty ORDER BY count DESC"
        )
        # Add missing specialties with zero count
        existing = {r["medical_specialty"] for r in rows}
        for spec in MEDICAL_SPECIALTIES:
            if spec not in existing:
                rows.append({"medical_specialty": spec, "count": 0})
        return rows

    def get_search_stats(self) -> dict[str, Any]:
        rows = self._query(
            "SELECT COUNT(*) as highly_used FROM terms WHERE usage_count > 0"
        )
        top = self._query(
            "SELECT english, arabic, usage_count FROM terms "
            "ORDER BY usage_count DESC LIMIT 10"
        )
        return {
            "terms_with_usage": rows[0]["highly_used"] if rows else 0,
            "top_terms": top,
        }

    def get_data_quality_score(self) -> dict[str, Any]:
        try:
            from .quality_checker import QualityChecker
        except ImportError:
            return {"score": None, "error": "QualityChecker not available"}

        qc = QualityChecker(db_manager=self.db)
        score = qc.get_quality_score()
        return {"score": score, "max": 100}

    def generate_text_report(self, fmt: str = "text") -> str:
        """Generate a human-readable text report."""
        overview = self.get_overview()
        sources = self.get_source_statistics()
        types = self.get_type_distribution()
        conf_dist = self.get_confidence_distribution()

        if fmt == "markdown":
            sep = "# "
            bold = "**"
        else:
            sep = ""
            bold = ""

        lines: list[str] = []
        lines.append(f"{sep}Glossary Statistics Report\n")
        lines.append(f"{bold}Total Terms:{bold} {overview['total_terms']:,}")
        lines.append(f"{bold}Total Sources:{bold} {overview['total_sources']}")
        lines.append(f"{bold}Database Size:{bold} {overview['database_size_mb']} MB\n")

        lines.append(f"{sep}Top Sources\n")
        for s in sources[:15]:
            lines.append(f"  {s['source']}: {s['count']:,} terms (avg conf: {s.get('avg_confidence', 0):.2f})")

        lines.append(f"\n{sep}Term Types\n")
        for t in types:
            lines.append(f"  {t['type']}: {t['count']:,}")

        lines.append(f"\n{sep}Confidence Distribution\n")
        for c in conf_dist:
            lines.append(f"  {c['range']}: {c['count']:,} (avg: {c.get('avg_conf', 0):.3f})")

        return "\n".join(lines)

    def generate_comparison_report(
        self, before: dict[str, Any], after: dict[str, Any]
    ) -> str:
        """Generate a comparison between two snapshots."""
        lines = ["# Comparison Report\n"]
        b_total = before.get("total_terms", 0)
        a_total = after.get("total_terms", 0)
        diff = a_total - b_total
        lines.append(f"Before: {b_total:,} terms")
        lines.append(f"After:  {a_total:,} terms")
        lines.append(f"Change: {diff:+,} terms\n")
        return "\n".join(lines)