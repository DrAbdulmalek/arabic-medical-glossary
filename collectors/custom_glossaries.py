"""
المجمع المخصص لملفات المسارد المحلية (CSV نظيفة + خام).
يقرأ من:
  - glossaries/           (86 ملف خام من منشآت دوائية)
  - cleaned/              (ملفات منظفة: terms, sentences, headers)
  - who_umd_terms.csv     (مصطلحات WHO UMD)
"""

import csv
import os
import re
import glob
from typing import List

from collectors.base import BaseCollector, TermEntry


class CustomGlossariesCollector(BaseCollector):
    """
    مجمع لملفات المسارد المحلية الموجودة في المشروع.
    يحول أزواج en/ar من ملفات CSV إلى TermEntry موحدة.
    """

    # الأقسام التي تمثل عناوين وليست مصطلحات قابلة للاستخدام
    # ملاحظة: header و dosage_form تحتوي أزواج ثنائية اللغة صالحة
    SKIP_SECTIONS = {"section", ""}

    # أنماط للصفوف غير المرغوب فيها
    JUNK_PATTERNS = [
        r'^HAMAPHARMA',
        r'^LEAF/',
        r'^\s*–\s*HAMAPHARMA',
        r'^\s*\*\*',
        r'^\(Arab ',
        r'^\(Council ',
        r'^Size:',
        r'^Packaging',
    ]

    def __init__(self, config: dict = None):
        super().__init__(
            "CustomGlossaries",
            "https://github.com/DrAbdulmalek/arabic-medical-glossary",
            config
        )

    def collect(self) -> int:
        new_count = 0

        # 1. ملفات glossaries/ الخام
        new_count += self._collect_glossaries_dir()

        # 2. ملفات cleaned/ المنظفة
        new_count += self._collect_cleaned_dir()

        # 3. ملف WHO UMD
        new_count += self._collect_who_umd()

        self.logger.info(f"✅ CustomGlossaries: {new_count} مصطلح جديد")
        return new_count

    # ------------------------------------------------------------------
    # 1. glossaries/  (86 ملف, أعمدة: en, ar, section)
    # ------------------------------------------------------------------
    def _collect_glossaries_dir(self) -> int:
        glossaries_dir = "glossaries"
        if not os.path.isdir(glossaries_dir):
            self.logger.warning(f"⚠️ المجلد {glossaries_dir} غير موجود")
            return 0

        new_count = 0
        csv_files = sorted(glob.glob(os.path.join(glossaries_dir, "*.csv")))
        self.logger.info(f"📂 العثور على {len(csv_files)} ملف في glossaries/")

        for csv_path in csv_files:
            filename = os.path.basename(csv_path).replace(".csv", "")
            try:
                count = self._process_raw_csv(csv_path, filename)
                new_count += count
            except Exception as e:
                self.logger.error(f"❌ خطأ في {filename}: {e}")

        return new_count

    def _process_raw_csv(self, csv_path: str, source_tag: str) -> int:
        """معالجة ملف خام من glossaries/"""
        new_count = 0

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                en = (row.get("en") or "").strip()
                ar = (row.get("ar") or "").strip()
                section = (row.get("section") or "").strip().lower()

                # تخطي الأقسام غير المفيدة
                if section in self.SKIP_SECTIONS:
                    continue

                # تخطي الصفوف غير المرغوب فيها
                if self._is_junk(en, ar):
                    continue

                # تنظيف النص
                en = self._clean_text(en)
                ar = self._clean_text(ar)

                if not en or not ar:
                    continue

                # تصنيف الثقة حسب طول النص
                confidence = self._classify_confidence(en, ar, section)

                # إضافة مصطلح إنجليزي مع ترجمة عربية
                entry_en = TermEntry(
                    term=en,
                    definition=ar,
                    source="CustomGlossaries",
                    language="en",
                    confidence=confidence,
                    tags=["local_csv", source_tag, section]
                )
                if self.add_term(entry_en):
                    new_count += 1

                # إضافة مصطلح عربي مع ترجمة إنجليزية (للبحث ثنائي الاتجاه)
                entry_ar = TermEntry(
                    term=ar,
                    definition=en,
                    source="CustomGlossaries",
                    language="ar",
                    confidence=confidence,
                    tags=["local_csv", source_tag, section]
                )
                if self.add_term(entry_ar):
                    new_count += 1

        return new_count

    # ------------------------------------------------------------------
    # 2. cleaned/  (terms.csv, sentences.csv, section_headers.csv, إلخ)
    # ------------------------------------------------------------------
    def _collect_cleaned_dir(self) -> int:
        cleaned_dir = "cleaned"
        if not os.path.isdir(cleaned_dir):
            self.logger.warning(f"⚠️ المجلد {cleaned_dir} غير موجود")
            return 0

        new_count = 0

        # ملف المصطلحات المنظفة (الأولوية القصوى)
        terms_path = os.path.join(cleaned_dir, "terms.csv")
        if os.path.exists(terms_path):
            new_count += self._process_cleaned_csv(terms_path, "cleaned_terms", 0.95)

        # ملف المصطلحات الشامل
        comprehensive_path = os.path.join(cleaned_dir, "comprehensive_glossary.csv")
        if os.path.exists(comprehensive_path):
            new_count += self._process_cleaned_csv(
                comprehensive_path, "comprehensive", 0.90
            )

        # ملف الجمل الطبية
        sentences_path = os.path.join(cleaned_dir, "sentences.csv")
        if os.path.exists(sentences_path):
            new_count += self._process_cleaned_csv(
                sentences_path, "medical_sentences", 0.80
            )

        # ملف العناوين
        headers_path = os.path.join(cleaned_dir, "section_headers.csv")
        if os.path.exists(headers_path):
            new_count += self._process_cleaned_csv(
                headers_path, "section_headers", 0.75
            )

        self.logger.info(f"📂 cleaned/: {new_count} مصطلح")
        return new_count

    def _process_cleaned_csv(
        self, csv_path: str, source_tag: str, base_confidence: float
    ) -> int:
        """معالجة ملف من cleaned/ (أعمدة: en, ar)"""
        new_count = 0

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                en = (row.get("en") or "").strip()
                ar = (row.get("ar") or "").strip()

                en = self._clean_text(en)
                ar = self._clean_text(ar)

                if not en or not ar:
                    continue
                if self._is_junk(en, ar):
                    continue

                # en → ar
                entry_en = TermEntry(
                    term=en, definition=ar,
                    source="CustomGlossaries", language="en",
                    confidence=base_confidence,
                    tags=["cleaned", source_tag]
                )
                if self.add_term(entry_en):
                    new_count += 1

                # ar → en
                entry_ar = TermEntry(
                    term=ar, definition=en,
                    source="CustomGlossaries", language="ar",
                    confidence=base_confidence,
                    tags=["cleaned", source_tag]
                )
                if self.add_term(entry_ar):
                    new_count += 1

        return new_count

    # ------------------------------------------------------------------
    # 3. who_umd_terms.csv
    # ------------------------------------------------------------------
    def _collect_who_umd(self) -> int:
        who_path = "who_umd_terms.csv"
        if not os.path.exists(who_path):
            self.logger.info("ℹ️ who_umd_terms.csv غير موجود — يتم التخطي")
            return 0

        new_count = 0
        self.logger.info("📂 معالجة who_umd_terms.csv")

        try:
            with open(who_path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)

                # اكتشاف أسماء الأعمدة تلقائياً
                fieldnames = reader.fieldnames or []
                en_key = self._find_column(fieldnames, ["en", "english", "term_en", "source_term"])
                ar_key = self._find_column(fieldnames, ["ar", "arabic", "term_ar", "target_term"])

                if not en_key or not ar_key:
                    self.logger.warning(
                        f"⚠️ لم يتم العثور على أعمدة en/ar. الأعمدة: {fieldnames[:5]}"
                    )
                    return 0

                for row in reader:
                    en = self._clean_text(row.get(en_key, "") or "")
                    ar = self._clean_text(row.get(ar_key, "") or "")

                    if not en or not ar or self._is_junk(en, ar):
                        continue

                    entry_en = TermEntry(
                        term=en, definition=ar,
                        source="WHO_UMD", language="en",
                        confidence=0.95,
                        tags=["who_umd"]
                    )
                    if self.add_term(entry_en):
                        new_count += 1

                    entry_ar = TermEntry(
                        term=ar, definition=en,
                        source="WHO_UMD", language="ar",
                        confidence=0.95,
                        tags=["who_umd"]
                    )
                    if self.add_term(entry_ar):
                        new_count += 1

        except Exception as e:
            self.logger.error(f"❌ خطأ في معالجة WHO UMD: {e}")

        return new_count

    # ------------------------------------------------------------------
    # أدوات مساعدة
    # ------------------------------------------------------------------
    def _is_junk(self, en: str, ar: str) -> bool:
        """تحديد ما إذا كان الصف غير مفيد"""
        for pattern in self.JUNK_PATTERNS:
            if re.match(pattern, en, re.IGNORECASE):
                return True

        # تخطي الأسطر القصيرة جداً
        if len(en) < 3 and len(ar) < 3:
            return True

        # تخطي الأسطر التي تحتوي على أرقام فقط
        if re.match(r'^[\d\s,.\-]+$', en):
            return True

        return False

    def _clean_text(self, text: str) -> str:
        """تنظيف النص من العناصر غير المرغوب فيها"""
        if not text:
            return ""

        # إزالة BOM
        text = text.lstrip("\ufeff")

        # إزالة علامات الترقيم الزائدة في البداية
        text = re.sub(r'^[\-\–\—\*\(\)\[\]\s]+', '', text)

        # إزالة مسافات متعددة
        text = re.sub(r'\s+', ' ', text)

        # إزالة علامات Markdown
        text = re.sub(r'\*+', '', text)

        return text.strip()

    def _classify_confidence(self, en: str, ar: str, section: str) -> float:
        """تصنيف الثقة حسب القسم وطول النص"""
        # الأقسام الموثوقة
        high_confidence_sections = {
            "indications", "mechanism_of_action",
            "pharmacokinetics", "contraindications",
            "side_effects", "dosage_and_administration",
            "drug_interactions", "warnings",
        }

        section_lower = section.lower().replace(" ", "_")

        if section_lower in high_confidence_sections:
            return 0.9
        elif len(en) > 5 and len(ar) > 5:
            return 0.85
        else:
            return 0.75

    @staticmethod
    def _find_column(fieldnames: list, candidates: list) -> str:
        """البحث عن عمود باسم مرشح"""
        if not fieldnames:
            return ""
        field_lower = [f.strip().lower() for f in fieldnames]
        for candidate in candidates:
            if candidate.lower() in field_lower:
                return fieldnames[field_lower.index(candidate.lower())]
        return ""