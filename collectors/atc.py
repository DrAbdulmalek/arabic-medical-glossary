"""
Collect medical terms from WHO ATC (Anatomical Therapeutic Chemical) Classification.

⚠️ ملاحظة هامة:
ATC لا يوفر REST API مباشر. يجب تحميل ملف XML/Excel من:
https://atcddd.fhi.no/atc_ddd_index_and_guidelines/atc_ddd_index/

يتطلب حساباً مسجلاً (مجاني) للوصول للملفات.

هذا المجمع يدعم:
1. تحميل الملف تلقائياً (إذا كان متاحاً عبر رابط مباشر)
2. قراءة ملف XML محلي (إذا قمت برفعه للمستودع)
3. البحث في النسخة المُحمَّلة مسبقاً

API Docs: https://atcddd.fhi.no/atc_ddd_index_and_guidelines/atc_ddd_index/
"""

import os
import json
import xml.etree.ElementTree as ET
from typing import List, Optional

from collectors.base import BaseCollector, TermEntry


class ATCCollector(BaseCollector):
    """
    مجمع مصطلحات من WHO ATC Classification
    يتطلب ملف XML/Excel يدوي أو رابط مباشر
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "ATC",
            "https://atcddd.fhi.no/",
            config
        )

        # مسارات الملفات المحتملة
        self.local_xml = os.path.join("data", "atc", "atc_index.xml")
        self.local_json = os.path.join("data", "atc", "atc_index.json")
        self.download_dir = os.path.join("data", "atc")
        os.makedirs(self.download_dir, exist_ok=True)

    def collect(self) -> int:
        """
        جمع المصطلحات من ATC
        يحاول أولاً قراءة ملف محلي، ثم يحاول التحميل
        """
        new_count = 0

        # محاولة 1: قراءة ملف JSON محلي (مُحوَّل مسبقاً)
        if os.path.exists(self.local_json):
            self.logger.info("📄 تم العثور على ملف JSON محلي")
            new_count = self._parse_json_file()
            return new_count

        # محاولة 2: قراءة ملف XML محلي
        if os.path.exists(self.local_xml):
            self.logger.info("📄 تم العثور على ملف XML محلي")
            new_count = self._parse_xml_file()
            # حفظ كـ JSON للمرة القادمة
            self._save_as_json()
            return new_count

        # محاولة 3: جلب من رابط مباشر (إذا توفر)
        try:
            new_count = self._fetch_from_url()
            if new_count > 0:
                return new_count
        except Exception as e:
            self.logger.warning(f"⚠️ فشل الجلب من الرابط: {e}")

        # إذا فشل كل شيء
        self.logger.warning(
            "⚠️ لم يتم العثور على ملف ATC.\n"
            "الرجاء:\n"
            "1. التسجيل في https://atcddd.fhi.no/\n"
            "2. تحميل ملف ATC Index (XML/Excel)\n"
            "3. وضعه في data/atc/atc_index.xml\n"
            "4. إعادة التشغيل"
        )

        return 0

    def _parse_xml_file(self) -> int:
        """تحليل ملف XML واستخراج المصطلحات"""
        new_count = 0

        try:
            tree = ET.parse(self.local_xml)
            root = tree.getroot()

            # البحث عن جميع عناصر ATC
            # هيكل XML النموذجي: <ATC><ATCCode code="A01"><Title>...</Title>...</ATCCode></ATC>
            for atc_code in root.iter("ATCCode"):
                code = atc_code.get("code", "")

                # البحث عن العنوان والتعريف
                title_elem = atc_code.find("Title")
                title = title_elem.text if title_elem is not None else ""

                if not code or not title:
                    continue

                # تحديد المستوى (1-5) بناءً على طول الكود
                level = len(code.replace(".", ""))

                entry = TermEntry(
                    term=title,
                    definition=f"ATC Code {code} (Level {level})",
                    source="ATC",
                    language="en",
                    confidence=0.95,
                    tags=["atc", code, f"level_{level}"]
                )

                if self.add_term(entry):
                    new_count += 1

            self.logger.info(f"✅ ATC XML: {new_count} مصطلح")

        except ET.ParseError as e:
            self.logger.error(f"❌ خطأ في تحليل XML: {e}")

        return new_count

    def _parse_json_file(self) -> int:
        """قراءة ملف JSON محلي"""
        new_count = 0

        try:
            with open(self.local_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for item in data:
                code = item.get("code", "")
                title = item.get("title", "")
                level = item.get("level", 0)

                if not code or not title:
                    continue

                entry = TermEntry(
                    term=title,
                    definition=f"ATC Code {code} (Level {level})",
                    source="ATC",
                    language="en",
                    confidence=0.95,
                    tags=["atc", code, f"level_{level}"]
                )

                if self.add_term(entry):
                    new_count += 1

            self.logger.info(f"✅ ATC JSON: {new_count} مصطلح")

        except Exception as e:
            self.logger.error(f"❌ خطأ في قراءة JSON: {e}")

        return new_count

    def _fetch_from_url(self) -> int:
        """محاولة جلب الملف من رابط مباشر (إذا توفر)"""
        # ملاحظة: WHO لا يوفر رابط مباشر للملف بدون تسجيل
        # هذا placeholder للمستقبل إذا توفر رابط
        self.logger.info("🔍 البحث عن رابط مباشر...")

        # يمكن إضافة رابط مباشر هنا إذا توفر
        # url = "https://example.com/atc_index.xml"
        # response = self.session.get(url, timeout=60)
        # ...

        return 0

    def _save_as_json(self):
        """حفظ البيانات المُحللة كـ JSON للاستخدام المستقبلي"""
        try:
            data = self.load_source_data()
            terms_list = []

            for term_hash, term_data in data.get("terms", {}).items():
                tags = term_data.get("tags", [])
                code = tags[1] if len(tags) > 1 else ""
                level = tags[2] if len(tags) > 2 else ""

                terms_list.append({
                    "code": code,
                    "title": term_data.get("term", ""),
                    "level": level.replace("level_", "") if level else ""
                })

            with open(self.local_json, 'w', encoding='utf-8') as f:
                json.dump(terms_list, f, ensure_ascii=False, indent=2)

            self.logger.info(f"💾 تم حفظ {len(terms_list)} مصطلح كـ JSON")

        except Exception as e:
            self.logger.error(f"❌ خطأ في حفظ JSON: {e}")

    def create_sample_data(self):
        """
        إنشاء بيانات نموذجية للاختبار
        يمكن استخدامه لإنشاء ملف JSON يدوياً
        """
        sample_data = [
            {"code": "A", "title": "ALIMENTARY TRACT AND METABOLISM", "level": "1"},
            {"code": "A01", "title": "STOMATOLOGICAL PREPARATIONS", "level": "2"},
            {"code": "A01A", "title": "STOMATOLOGICAL PREPARATIONS", "level": "3"},
            {"code": "A01AA", "title": "Caries prophylactic agents", "level": "4"},
            {"code": "A01AA01", "title": "Sodium fluoride", "level": "5"},
            {"code": "B", "title": "BLOOD AND BLOOD FORMING ORGANS", "level": "1"},
            {"code": "B01", "title": "ANTITHROMBOTIC AGENTS", "level": "2"},
            {"code": "B01A", "title": "ANTITHROMBOTIC AGENTS", "level": "3"},
            {"code": "B01AA", "title": "Vitamin K antagonists", "level": "4"},
            {"code": "B01AA01", "title": "Dicoumarol", "level": "5"},
            {"code": "C", "title": "CARDIOVASCULAR SYSTEM", "level": "1"},
            {"code": "C01", "title": "CARDIAC THERAPY", "level": "2"},
            {"code": "C01A", "title": "CARDIAC GLYCOSIDES", "level": "3"},
            {"code": "C01AA", "title": "Digitalis glycosides", "level": "4"},
            {"code": "C01AA01", "title": "Acetyldigoxin", "level": "5"},
            {"code": "J", "title": "ANTIINFECTIVES FOR SYSTEMIC USE", "level": "1"},
            {"code": "J01", "title": "ANTIBACTERIALS FOR SYSTEMIC USE", "level": "2"},
            {"code": "J01A", "title": "TETRACYCLINES", "level": "3"},
            {"code": "J01AA", "title": "Tetracyclines", "level": "4"},
            {"code": "J01AA01", "title": "Demeclocycline", "level": "5"},
            {"code": "N", "title": "NERVOUS SYSTEM", "level": "1"},
            {"code": "N02", "title": "ANALGESICS", "level": "2"},
            {"code": "N02A", "title": "OPIOIDS", "level": "3"},
            {"code": "N02AA", "title": "Natural opium alkaloids", "level": "4"},
            {"code": "N02AA01", "title": "Morphine", "level": "5"},
        ]

        with open(self.local_json, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"✅ تم إنشاء {len(sample_data)} مصطلح نموذجي")
        return len(sample_data)
