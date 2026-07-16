"""
Collect medical terms from ICHI (International Classification of Health Interventions).
Developed by WHO as a successor to ICD-9-CM Volume 3 and ICPM.

⚠️ ملاحظة:
ICHI لا يوفر REST API مباشر. يجب تحميل ملفات من:
https://www.who.int/standards/classifications/classification-of-health-interventions

يتطلب حساباً مسجلاً (مجاني) للوصول للملفات.

هذا المجمع يدعم:
1. قراءة ملف CSV/Excel محلي
2. إنشاء بيانات نموذجية للاختبار
"""

import os
import json
from collectors.base import BaseCollector, TermEntry


class ICHICollector(BaseCollector):
    """
    مجمع مصطلحات من ICHI (WHO)
    يتطلب تحميل ملف يدوي
    """

    def __init__(self, config: dict = None):
        super().__init__(
            "ICHI",
            "https://www.who.int/standards/classifications/classification-of-health-interventions",
            config
        )

        self.download_dir = os.path.join("data", "ichi")
        self.local_json = os.path.join(self.download_dir, "ichi_index.json")
        os.makedirs(self.download_dir, exist_ok=True)

    def collect(self) -> int:
        """
        جمع المصطلحات من ICHI
        يحاول قراءة ملف محلي ثم يحاول إنشاء بيانات نموظية
        """
        new_count = 0

        # محاولة 1: قراءة ملف JSON محلي
        if os.path.exists(self.local_json):
            self.logger.info("📄 تم العثور على ملف JSON محلي")
            new_count = self._parse_json_file()
            return new_count

        # محاولة 2: إنشاء بيانات نموظية
        self.logger.warning(
            "⚠️ لم يتم العثور على ملف ICHI.\n"
            "الرجاء:\n"
            "1. التسجيل في https://www.who.int/standards/classifications/\n"
            "2. تحميل ملف ICHI (CSV/Excel)\n"
            "3. وضعه في data/ichi/\n"
            "4. أو استخدام create_sample_data()"
        )

        return 0

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
                    definition=f"ICHI Code: {code} (Level {level})",
                    source="ICHI",
                    language="en",
                    confidence=0.95,
                    tags=["ichi", code, f"level_{level}"]
                )

                if self.add_term(entry):
                    new_count += 1

            self.logger.info(f"✅ ICHI JSON: {new_count} مصطلح")

        except Exception as e:
            self.logger.error(f"❌ خطأ في قراءة JSON: {e}")

        return new_count

    def create_sample_data(self) -> int:
        """
        إنشاء بيانات نموذجية للاختبار
        """
        sample_data = [
            {"code": "1", "title": "Diagnostic interventions", "level": "1"},
            {"code": "1.1", "title": "History-taking", "level": "2"},
            {"code": "1.1.1", "title": "Taking history of presenting problem", "level": "3"},
            {"code": "1.2", "title": "Physical examination", "level": "2"},
            {"code": "1.2.1", "title": "General physical examination", "level": "3"},
            {"code": "1.3", "title": "Diagnostic imaging", "level": "2"},
            {"code": "1.3.1", "title": "Plain X-ray imaging", "level": "3"},
            {"code": "1.3.2", "title": "Computed tomography", "level": "3"},
            {"code": "1.3.3", "title": "Magnetic resonance imaging", "level": "3"},
            {"code": "1.3.4", "title": "Ultrasound imaging", "level": "3"},
            {"code": "2", "title": "Therapeutic interventions", "level": "1"},
            {"code": "2.1", "title": "Pharmacotherapy", "level": "2"},
            {"code": "2.1.1", "title": "Administration of oral medication", "level": "3"},
            {"code": "2.1.2", "title": "Administration of injectable medication", "level": "3"},
            {"code": "2.2", "title": "Surgical procedures", "level": "2"},
            {"code": "2.2.1", "title": "Incision and drainage", "level": "3"},
            {"code": "2.2.2", "title": "Excision and biopsy", "level": "3"},
            {"code": "3", "title": "Rehabilitative interventions", "level": "1"},
            {"code": "3.1", "title": "Physical therapy", "level": "2"},
            {"code": "3.1.1", "title": "Therapeutic exercise", "level": "3"},
            {"code": "3.1.2", "title": "Manual therapy", "level": "3"},
            {"code": "3.2", "title": "Occupational therapy", "level": "2"},
            {"code": "3.2.1", "title": "Activities of daily living training", "level": "3"},
            {"code": "4", "title": "Supportive interventions", "level": "1"},
            {"code": "4.1", "title": "Nutritional support", "level": "2"},
            {"code": "4.1.1", "title": "Enteral nutrition", "level": "3"},
            {"code": "4.1.2", "title": "Parenteral nutrition", "level": "3"},
            {"code": "4.2", "title": "Psychological support", "level": "2"},
            {"code": "4.2.1", "title": "Counseling", "level": "3"},
        ]

        with open(self.local_json, 'w', encoding='utf-8') as f:
            json.dump(sample_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"✅ تم إنشاء {len(sample_data)} مصطلح نموذجي")
        return len(sample_data)
