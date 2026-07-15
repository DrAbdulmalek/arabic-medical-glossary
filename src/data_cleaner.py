"""Data cleaning utilities for Arabic-English medical term pairs."""

import hashlib
import logging
import re
from difflib import SequenceMatcher
from typing import Any, Optional

from .config import CONFIDENCE_LEVELS, TERM_TYPES

logger = logging.getLogger(__name__)


class DataCleaner:
    """Static methods for normalising, validating and deduplicating glossary data."""

    # Tashkeel Unicode range plus tatweel U+0640 and super-script alef U+0670
    _TASHKEEL_RE = re.compile(r"[\u064B-\u065F\u0670\u0640]")

    @staticmethod
    def clean_english(text: str) -> str:
        """Lowercase and strip non-alphanumeric characters except -(), comma.&/space."""
        if not text:
            return ""
        text = text.strip().lower()
        text = re.sub(r"[^a-z0-9\s\-\(\)\,\.\&\/]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def clean_arabic(text: str) -> str:
        """Remove tashkeel, keep only Arabic block characters plus whitespace."""
        if not text:
            return ""
        text = DataCleaner._TASHKEEL_RE.sub("", text)
        text = re.sub(r"[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def remove_markdown(text: str) -> str:
        """Strip common Markdown constructs."""
        if not text:
            return ""
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\(.*?\)", r"\1", text)
        for ch in ("**", "__", "~~", "##", ">>", "__"):
            text = text.replace(ch, "")
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
        return text.strip()

    @staticmethod
    def remove_html(text: str) -> str:
        """Remove HTML tags and decode common entities."""
        if not text:
            return ""
        text = re.sub(r"<br\s*/?>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"&quot;", '"', text)
        text = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), text)
        text = re.sub(r"&[a-zA-Z]+;", "", text)
        return text.strip()

    @staticmethod
    def remove_extra_whitespace(text: str) -> str:
        """Collapse runs of whitespace and strip edges."""
        if not text:
            return ""
        return re.sub(r"[ \t\r\n]+", " ", text).strip()

    @staticmethod
    def normalize_term(text: str, lang: str = "en") -> str:
        """Full normalization pipeline for a single term."""
        if not text:
            return ""
        text = DataCleaner.remove_html(text)
        text = DataCleaner.remove_markdown(text)
        if lang == "ar":
            text = DataCleaner.clean_arabic(text)
        else:
            text = DataCleaner.clean_english(text)
        return DataCleaner.remove_extra_whitespace(text)

    @staticmethod
    def normalize_confidence(value: Any) -> float:
        """Map string confidence levels to numeric values."""
        if isinstance(value, (int, float)):
            return float(max(0.0, min(1.0, value)))
        if isinstance(value, str):
            lower = value.strip().lower()
            return CONFIDENCE_LEVELS.get(lower, 0.5)
        return 0.5

    @staticmethod
    def normalize_type(value: Any) -> str:
        """Normalise a term type string."""
        if not value:
            return "term"
        cleaned = str(value).strip().lower().replace(" ", "_").replace("-", "_")
        if cleaned in TERM_TYPES:
            return cleaned
        for t in TERM_TYPES:
            if cleaned in t or t in cleaned:
                return t
        return "term"

    @staticmethod
    def validate_english(text: str) -> tuple[bool, str]:
        """Return (is_valid, reason) for an English term."""
        if not text or not text.strip():
            return False, "empty_string"
        cleaned = text.strip()
        if len(cleaned) < 1:
            return False, "too_short"
        # Must contain at least one ASCII letter
        if not re.search(r"[a-zA-Z]", cleaned):
            return False, "no_latin_letters"
        if re.search(r"[\u0600-\u06FF]", cleaned):
            return False, "contains_arabic"
        if len(cleaned) > 500:
            return False, "too_long"
        return True, "ok"

    @staticmethod
    def validate_arabic(text: str) -> tuple[bool, str]:
        """Return (is_valid, reason) for an Arabic term."""
        if not text or not text.strip():
            return False, "empty_string"
        cleaned = text.strip()
        if len(cleaned) < 1:
            return False, "too_short"
        if not re.search(r"[\u0600-\u06FF]", cleaned):
            return False, "no_arabic_chars"
        if len(cleaned) > 500:
            return False, "too_long"
        return True, "ok"

    @staticmethod
    def deduplicate_terms(terms: list[dict]) -> list[dict]:
        """Remove duplicates keyed on (english, arabic), keeping highest confidence."""
        seen: dict[tuple[str, str], dict] = {}
        for t in terms:
            key = (t.get("english", "").strip().lower(), t.get("arabic", "").strip())
            existing = seen.get(key)
            if existing is None or t.get("confidence", 0) > existing.get("confidence", 0):
                seen[key] = t
        return list(seen.values())

    @staticmethod
    def generate_hash(english: str, arabic: str) -> str:
        """MD5 hash of normalised english||arabic."""
        raw = english.lower().strip() + "||" + arabic.strip()
        return hashlib.md5(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def batch_clean(terms: list[dict]) -> list[dict]:
        """Apply full cleaning pipeline to a list of term dicts."""
        cleaned = []
        for t in terms:
            ct = dict(t)
            if "english" in ct:
                ct["english"] = DataCleaner.normalize_term(ct["english"], "en")
            if "arabic" in ct:
                ct["arabic"] = DataCleaner.normalize_term(ct["arabic"], "ar")
            if "confidence" in ct:
                ct["confidence"] = DataCleaner.normalize_confidence(ct["confidence"])
            if "type" in ct:
                ct["type"] = DataCleaner.normalize_type(ct["type"])
            if "hash" not in ct or not ct["hash"]:
                ct["hash"] = DataCleaner.generate_hash(
                    ct.get("english", ""), ct.get("arabic", "")
                )
            cleaned.append(ct)
        return cleaned

    @staticmethod
    def clean_csv_row(row: dict) -> dict:
        """Clean a single CSV row dict."""
        cleaned = {}
        for k, v in row.items():
            if isinstance(v, str):
                v = DataCleaner.remove_html(v)
                v = DataCleaner.remove_markdown(v)
                v = DataCleaner.remove_extra_whitespace(v)
            cleaned[k] = v
        if "english" in cleaned:
            cleaned["english"] = DataCleaner.clean_english(cleaned["english"])
        if "arabic" in cleaned:
            cleaned["arabic"] = DataCleaner.clean_arabic(cleaned["arabic"])
        return cleaned

    @staticmethod
    def clean_dataframe(df: "Any") -> "Any":  # pragma: no cover — pandas optional
        """Clean a pandas DataFrame in-place and return it."""
        try:
            import pandas as pd
        except ImportError:
            logger.error("pandas is required for clean_dataframe")
            return df

        if "english" in df.columns:
            df["english"] = df["english"].astype(str).apply(
                lambda x: DataCleaner.normalize_term(x, "en")
            )
        if "arabic" in df.columns:
            df["arabic"] = df["arabic"].astype(str).apply(
                lambda x: DataCleaner.normalize_term(x, "ar")
            )
        if "confidence" in df.columns:
            df["confidence"] = df["confidence"].apply(
                DataCleaner.normalize_confidence
            )
        if "type" in df.columns:
            df["type"] = df["type"].apply(DataCleaner.normalize_type)
        if "hash" not in df.columns:
            df["hash"] = df.apply(
                lambda r: DataCleaner.generate_hash(r.get("english", ""), r.get("arabic", "")),
                axis=1,
            )
        return df