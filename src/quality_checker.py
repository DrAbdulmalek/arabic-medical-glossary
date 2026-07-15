"""Quality checking for the Arabic Medical Glossary."""

import logging
import re
from difflib import SequenceMatcher
from typing import Any, Optional

from .config import (
    HIGH_CONFIDENCE_THRESHOLD,
    MAX_ARABIC_LENGTH,
    MAX_DUPLICATE_RATIO,
    MAX_ENGLISH_LENGTH,
    MAX_LATIN_IN_ARABIC_RATIO,
    MIN_CONFIDENCE_THRESHOLD,
)

logger = logging.getLogger(__name__)


class QualityChecker:
    """Runs quality checks on glossary term data."""

    def __init__(self, db_manager: Any = None) -> None:
        self.db = db_manager

    def _get_terms(self) -> list[dict]:
        if self.db:
            return self.db.search(limit=500_000)
        return []

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------
    def check_duplicates(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find exact duplicates (same english+arabic)."""
        data = terms or self._get_terms()
        seen: dict[tuple[str, str], dict] = {}
        dupes: list[dict] = []
        for t in data:
            key = (str(t.get("english", "")).strip().lower(), str(t.get("arabic", "")).strip())
            if key in seen:
                dupes.append({"term": t, "duplicate_of": seen[key]})
            else:
                seen[key] = t
        return dupes

    def check_near_duplicates(
        self, terms: Optional[list[dict]] = None, threshold: float = 0.9
    ) -> list[dict]:
        """Find near-duplicates using SequenceMatcher on English terms."""
        data = terms or self._get_terms()
        results: list[dict] = []
        for i in range(len(data)):
            for j in range(i + 1, len(data)):
                en_i = str(data[i].get("english", "")).lower()
                en_j = str(data[j].get("english", "")).lower()
                ratio = SequenceMatcher(None, en_i, en_j).ratio()
                if ratio >= threshold:
                    results.append({
                        "term_a": data[i],
                        "term_b": data[j],
                        "similarity": round(ratio, 4),
                    })
        return results

    def check_empty_fields(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find terms with empty english or arabic fields."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        for t in data:
            en = str(t.get("english", "")).strip()
            ar = str(t.get("arabic", "")).strip()
            if not en:
                issues.append({"term": t, "issue": "empty_english"})
            if not ar:
                issues.append({"term": t, "issue": "empty_arabic"})
        return issues

    def check_arabic_cleanliness(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Check Arabic text for tashkeel, HTML, markdown, excessive Latin chars."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        tashkeel_re = re.compile(r"[\u064B-\u065F\u0670\u0640]")
        for t in data:
            ar = str(t.get("arabic", ""))
            if not ar:
                continue
            if tashkeel_re.search(ar):
                issues.append({"term": t, "issue": "contains_tashkeel"})
            if "<" in ar and ">" in ar:
                issues.append({"term": t, "issue": "contains_html"})
            if re.search(r"[#*_\[\]]", ar):
                issues.append({"term": t, "issue": "contains_markdown"})
            # Latin ratio
            latin_chars = sum(1 for c in ar if c.isascii() and c.isalpha())
            total_alpha = sum(1 for c in ar if c.isalpha())
            if total_alpha > 0 and (latin_chars / total_alpha) > MAX_LATIN_IN_ARABIC_RATIO:
                issues.append({"term": t, "issue": "high_latin_ratio"})
        return issues

    def check_english_cleanliness(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Check English text for HTML, markdown, non-Latin characters."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        for t in data:
            en = str(t.get("english", ""))
            if not en:
                continue
            if "<" in en and ">" in en:
                issues.append({"term": t, "issue": "contains_html"})
            if re.search(r"[#*_\[\]]", en):
                issues.append({"term": t, "issue": "contains_markdown"})
            if re.search(r"[\u0600-\u06FF]", en):
                issues.append({"term": t, "issue": "contains_arabic"})
        return issues

    def check_confidence_range(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find terms with confidence outside [0, 1] range."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        for t in data:
            conf = t.get("confidence")
            try:
                conf_f = float(conf)
                if conf_f < 0.0 or conf_f > 1.0:
                    issues.append({"term": t, "issue": "confidence_out_of_range", "value": conf_f})
            except (TypeError, ValueError):
                issues.append({"term": t, "issue": "invalid_confidence", "value": conf})
        return issues

    def check_term_length(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find terms exceeding maximum length."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        for t in data:
            en = str(t.get("english", ""))
            ar = str(t.get("arabic", ""))
            if len(en) > MAX_ENGLISH_LENGTH:
                issues.append({"term": t, "issue": "english_too_long", "length": len(en)})
            if len(ar) > MAX_ARABIC_LENGTH:
                issues.append({"term": t, "issue": "arabic_too_long", "length": len(ar)})
        return issues

    def check_source_consistency(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find terms with empty or inconsistent source fields."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        for t in data:
            src = str(t.get("source", "")).strip()
            if not src:
                issues.append({"term": t, "issue": "empty_source"})
        return issues

    def check_type_consistency(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find terms with unusual or empty type fields."""
        data = terms or self._get_terms()
        valid_types = {
            "term", "abbreviation", "phrase", "sentence", "drug_name",
            "brand_name", "generic_name", "medical_device", "anatomy",
            "procedure", "diagnosis", "symptom", "lab_test", "unit",
        }
        issues: list[dict] = []
        for t in data:
            tp = str(t.get("type", "")).strip().lower()
            if not tp:
                issues.append({"term": t, "issue": "empty_type"})
            elif tp not in valid_types:
                issues.append({"term": t, "issue": "unknown_type", "value": tp})
        return issues

    def check_self_translation(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find terms where English and Arabic are suspiciously similar (Latin in Arabic)."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        for t in data:
            en = str(t.get("english", "")).strip().lower()
            ar = str(t.get("arabic", "")).strip()
            ar_latin = re.sub(r"[^\u0000-\u007F]", "", ar).strip().lower()
            if en and ar_latin and en == ar_latin and len(en) > 2:
                issues.append({"term": t, "issue": "self_translation"})
        return issues

    def check_encoding_issues(self, terms: Optional[list[dict]] = None) -> list[dict]:
        """Find terms with encoding problems: replacement chars, HTML entities, mojibake."""
        data = terms or self._get_terms()
        issues: list[dict] = []
        for t in data:
            for field in ("english", "arabic"):
                val = str(t.get(field, ""))
                if "\ufffd" in val:
                    issues.append({"term": t, "issue": "replacement_character", "field": field})
                if re.search(r"&[a-zA-Z]+;", val):
                    issues.append({"term": t, "issue": "html_entity", "field": field})
                # Mojibake: many accented Latin chars in what should be Arabic
                if field == "arabic" and re.search(r"[àáâãäåèéêëìíîïòóôõöùúûüÿ]", val):
                    issues.append({"term": t, "issue": "mojibake", "field": field})
        return issues

    # ------------------------------------------------------------------
    # Composite checks
    # ------------------------------------------------------------------
    def check_all(self, terms: Optional[list[dict]] = None) -> dict[str, list]:
        """Run all quality checks and return a dict of check_name -> issues."""
        data = terms or self._get_terms()
        return {
            "duplicates": self.check_duplicates(data),
            "near_duplicates": self.check_near_duplicates(data, threshold=0.95)[:100],
            "empty_fields": self.check_empty_fields(data),
            "arabic_cleanliness": self.check_arabic_cleanliness(data),
            "english_cleanliness": self.check_english_cleanliness(data),
            "confidence_range": self.check_confidence_range(data),
            "term_length": self.check_term_length(data),
            "source_consistency": self.check_source_consistency(data),
            "type_consistency": self.check_type_consistency(data),
            "self_translation": self.check_self_translation(data),
            "encoding_issues": self.check_encoding_issues(data),
        }

    def generate_quality_report(self, terms: Optional[list[dict]] = None) -> str:
        """Return a Markdown quality report."""
        results = self.check_all(terms)
        lines = ["# Quality Report\n"]
        lines.append(f"**Total terms checked:** {len(terms or self._get_terms())}\n")
        lines.append("---\n")
        for name, issues in results.items():
            status = "✅ PASS" if not issues else f"⚠️ {len(issues)} issues"
            lines.append(f"## {name.replace('_', ' ').title()}: {status}\n")
            if issues:
                for issue in issues[:5]:
                    t = issue.get("term", {})
                    en = str(t.get("english", ""))[:50]
                    lines.append(f"- `{en}` — {issue.get('issue', '')}")
                if len(issues) > 5:
                    lines.append(f"- ... and {len(issues) - 5} more")
            lines.append("")
        return "\n".join(lines)

    def get_quality_score(self, terms: Optional[list[dict]] = None) -> float:
        """Return an overall quality score from 0 to 100 (weighted)."""
        data = terms or self._get_terms()
        if not data:
            return 0.0
        n = len(data)

        # Weights for each check category
        weights = {
            "duplicates": 20,
            "empty_fields": 15,
            "arabic_cleanliness": 15,
            "english_cleanliness": 10,
            "confidence_range": 10,
            "term_length": 5,
            "encoding_issues": 10,
            "self_translation": 10,
            "type_consistency": 5,
        }

        total_weight = sum(weights.values())
        weighted_score = 0.0

        checks = self.check_all(data)
        for check_name, weight in weights.items():
            issues = checks.get(check_name, [])
            # Deduplicate by term id to avoid double-counting
            issue_term_ids = set()
            for iss in issues:
                t = iss.get("term", {})
                issue_term_ids.add(id(t))
            issue_ratio = len(issue_term_ids) / max(n, 1)
            check_score = max(0.0, 1.0 - issue_ratio)
            weighted_score += (weight / total_weight) * check_score

        return round(weighted_score * 100, 2)