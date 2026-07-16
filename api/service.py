"""
طبقة الوصول للبيانات — تحميل وفلترة وبحث في المسرد.
"""

import json
import os
import re
import threading
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class GlossaryService:
    """
    خدمة المسرد — أحادية النسخة (Singleton).
    تحمل البيانات مرة واحدة وتحتفظ بها في الذاكرة.
    """
    _instance = None
    _lock = threading.Lock()

    MERGED_FILE = Path("data/merged/glossary_master.json")
    SOURCES_DIR = Path("data/sources")

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._terms: Dict[str, dict] = {}
        self._metadata: dict = {}
        self._by_language: Dict[str, List[str]] = {}
        self._by_source: Dict[str, List[str]] = {}
        self._en_to_ar: Dict[str, List[str]] = {}  # EN term → list of AR hash keys
        self._load_data()

    def _load_data(self):
        """تحميل البيانات المدمجة في الذاكرة مع بناء فهارس."""
        if not self.MERGED_FILE.exists():
            # Fallback: تحميل من ملفات المصادر المباشرة
            self._load_from_sources()
            return

        with open(self.MERGED_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._terms = data.get("terms", {})
        self._metadata = data.get("metadata", {})
        self._by_language = data.get("by_language", {})
        self._by_source = data.get("by_source", {})

        # بناء فهرس EN→AR للبحث الثنائي اللغة
        for hash_key, term_data in self._terms.items():
            lang = term_data.get("language", "")
            term_text = term_data.get("term", "").lower().strip()
            if lang == "en":
                self._en_to_ar.setdefault(term_text, []).append(hash_key)
            elif lang == "ar":
                # عكس: بناء فهرس AR→EN أيضاً
                self._en_to_ar.setdefault(term_text, []).append(hash_key)

    def _load_from_sources(self):
        """تحميل بديل من ملفات المصادر الفردية."""
        if not self.SOURCES_DIR.exists():
            return
        for fp in self.SOURCES_DIR.glob("*.json"):
            try:
                with open(fp, 'r', encoding='utf-8') as f:
                    src = json.load(f)
                for hash_key, term_data in src.get("terms", {}).items():
                    self._terms[hash_key] = term_data
            except Exception:
                continue
        self._build_indices()

    def _build_indices(self):
        """بناء الفهارس من _terms."""
        self._by_language = {"ar": [], "en": []}
        self._by_source = {}
        self._en_to_ar = {}
        for hash_key, td in self._terms.items():
            lang = td.get("language", "unknown")
            self._by_language.setdefault(lang, []).append(hash_key)
            src = td.get("source", "unknown")
            self._by_source.setdefault(src, []).append(hash_key)
            term_text = td.get("term", "").lower().strip()
            self._en_to_ar.setdefault(term_text, []).append(hash_key)

    # ─── عمليات البحث ────────────────────────────────────────────

    def search(
        self,
        query: str,
        language: Optional[str] = None,
        source: Optional[str] = None,
        min_confidence: Optional[float] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """
        بحث في المصطلحات مع دعمPagination.
        يُرجع (نتائج, إجمالي_المتطابقات).
        """
        query_lower = query.lower().strip()
        results = []
        seen_hashes = set()

        # 1. بحث نصي مباشر
        for hash_key, td in self._terms.items():
            term_text = td.get("term", "").lower()
            def_text = td.get("definition", "").lower()

            if query_lower not in term_text and query_lower not in def_text:
                continue

            # تطبيق الفلاتر
            if language and td.get("language") != language:
                continue
            if source and td.get("source") != source:
                continue
            if min_confidence is not None and td.get("confidence", 0) < min_confidence:
                continue
            if tags:
                term_tags = set(td.get("tags", []))
                if not term_tags.intersection(tags):
                    continue

            results.append(td)
            seen_hashes.add(hash_key)

        # 2. بحث ثنائي اللغة: إذا كان البحث EN، أضف المرادفات AR (والعكس)
        self._add_bilingual_matches(query_lower, results, seen_hashes, language, source, min_confidence, tags)

        total = len(results)
        paginated = results[offset:offset + limit]
        return paginated, total

    def _add_bilingual_matches(
        self, query_lower: str, results: list, seen_hashes: set,
        language: Optional[str], source: Optional[str],
        min_confidence: Optional[float], tags: Optional[List[str]],
    ):
        """إضافة تطابقات ثنائية اللغة — إذا وجد تطابق EN يُضيف AR والعكس."""
        matched_keys = self._en_to_ar.get(query_lower, [])
        if not matched_keys:
            return

        for hash_key in matched_keys:
            if hash_key in seen_hashes:
                continue
            td = self._terms.get(hash_key)
            if not td:
                continue

            # تخطي إذا كان نفس اللغة المطلوبة (لأنه مُضاف مسبقاً)
            if language and td.get("language") == language:
                continue
            if source and td.get("source") != source:
                continue
            if min_confidence is not None and td.get("confidence", 0) < min_confidence:
                continue
            if tags:
                term_tags = set(td.get("tags", []))
                if not term_tags.intersection(tags):
                    continue

            results.append(td)
            seen_hashes.add(hash_key)

    # ─── عمليات التصفح ───────────────────────────────────────────

    def get_term(self, term: str) -> List[dict]:
        """جلب جميع إصدارات مصطلح (EN + AR + مصادر متعددة)."""
        term_lower = term.lower().strip()
        matches = []
        for hash_key, td in self._terms.items():
            if td.get("term", "").lower().strip() == term_lower:
                matches.append(td)
        return matches

    def get_bilingual_pairs(self, term: str) -> List[dict]:
        """جلب أزواج EN-AR لمصطلح معين."""
        term_lower = term.lower().strip()
        # البحث عن كل المصطلحات التي تحمل هذا الاسم في أي لغة
        en_matches = []
        ar_matches = []

        for hash_key in self._en_to_ar.get(term_lower, []):
            td = self._terms.get(hash_key)
            if not td:
                continue
            if td.get("language") == "en":
                en_matches.append(td)
            elif td.get("language") == "ar":
                ar_matches.append(td)

        pairs = []
        for en in en_matches:
            for ar in ar_matches:
                if en.get("source") == ar.get("source"):
                    pairs.append({
                        "en_term": en.get("term", ""),
                        "ar_term": ar.get("term", ""),
                        "en_definition": en.get("definition", ""),
                        "ar_definition": ar.get("definition", ""),
                        "source": en.get("source", ""),
                        "confidence": min(en.get("confidence", 0), ar.get("confidence", 0)),
                    })
        return pairs

    def browse(
        self,
        language: Optional[str] = None,
        source: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[dict], int]:
        """تصفح المصطلحات معPagination."""
        filtered = list(self._terms.values())

        if language:
            filtered = [t for t in filtered if t.get("language") == language]
        if source:
            filtered = [t for t in filtered if t.get("source") == source]

        total = len(filtered)
        paginated = filtered[offset:offset + limit]
        return paginated, total

    def random_terms(self, count: int = 5, language: Optional[str] = None) -> List[dict]:
        """مصطلحات عشوائية — مفيد للـ Dashboard و RTL."""
        import random
        filtered = list(self._terms.values())
        if language:
            filtered = [t for t in filtered if t.get("language") == language]
        if count > len(filtered):
            count = len(filtered)
        return random.sample(filtered, count) if filtered else []

    # ─── الإحصائيات ──────────────────────────────────────────────

    def get_stats(self) -> dict:
        """إحصائيات شاملة عن المسرد."""
        by_lang = {}
        for lang, keys in self._by_language.items():
            by_lang[lang] = len(keys)

        by_src = {}
        for src, keys in self._by_source.items():
            by_src[src] = len(keys)

        sources_info = self._metadata.get("sources", [])

        return {
            "total_terms": len(self._terms),
            "by_language": by_lang,
            "by_source": by_src,
            "sources": sources_info,
            "metadata": self._metadata,
        }

    @property
    def total_terms(self) -> int:
        return len(self._terms)

    def reload(self):
        """إعادة تحميل البيانات (بعد تحديث)."""
        self._terms.clear()
        self._by_language.clear()
        self._by_source.clear()
        self._en_to_ar.clear()
        self._load_data()