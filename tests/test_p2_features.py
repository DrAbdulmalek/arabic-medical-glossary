"""
اختبارات NER Extractor و Active Learning.
"""

import json
import os
import sys
import tempfile
import shutil
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processors.ner_extractor import MedicalNERExtractor
from processors.active_learning import ActiveLearningManager, ReviewItem


class TestMedicalNER(unittest.TestCase):
    """اختبارات مستخرج الكيانات الطبية."""

    def setUp(self):
        self.extractor = MedicalNERExtractor()

    def test_english_disease(self):
        """استخراج مرض إنجليزي."""
        entities = self.extractor.extract("The patient has diabetes mellitus")
        labels = [e.label for e in entities]
        self.assertIn("DISEASE", labels)
        self.assertTrue(any("diabetes" in e.text.lower() for e in entities))

    def test_arabic_disease(self):
        """استخراج مرض عربي."""
        entities = self.extractor.extract("المريض يعاني من السكري")
        labels = [e.label for e in entities]
        self.assertIn("DISEASE", labels)

    def test_symptom_extraction(self):
        """استخراج أعراض."""
        entities = self.extractor.extract("fever and headache")
        labels = [e.label for e in entities]
        self.assertIn("SYMPTOM", labels)

    def test_drug_extraction(self):
        """استخراج أدوية."""
        entities = self.extractor.extract("prescribed metformin and aspirin")
        labels = [e.label for e in entities]
        self.assertIn("DRUG", labels)

    def test_procedure_extraction(self):
        """استخراج إجراءات طبية."""
        entities = self.extractor.extract("recommended biopsy and CT scan")
        labels = [e.label for e in entities]
        self.assertIn("PROCEDURE", labels)

    def test_no_overlap(self):
        """عدم تداخل الكيانات."""
        text = "diabetes mellitus"
        entities = self.extractor.extract(text)
        # لا يجب أن يكون هناك تداخل في الفترات
        for i, e1 in enumerate(entities):
            for e2 in entities[i+1:]:
                self.assertFalse(e1.start < e2.end and e2.start < e1.end)

    def test_glossary_matching(self):
        """مطابقة مع المسرد."""
        # إنشاء مسرد مؤقت
        tmp_dir = tempfile.mkdtemp()
        glossary_path = os.path.join(tmp_dir, "test_glossary.json")
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump({
                "terms": {
                    "abc123": {"term": "hypoglycemia", "definition": "انخفاض السكر", "confidence": 0.95, "source": "Test"}
                }
            }, f)

        ext = MedicalNERExtractor(glossary_path=glossary_path)
        entities = ext.extract("monitor for hypoglycemia")
        labels = [e.label for e in entities]
        # يجب أن يُطابَق كمصطلح طبي
        self.assertTrue(len(entities) > 0)

        shutil.rmtree(tmp_dir)

    def test_empty_text(self):
        """نص فارغ."""
        entities = self.extractor.extract("")
        self.assertEqual(len(entities), 0)

    def test_mixed_arabic_english(self):
        """نص عربي-إنجليزي مختلط."""
        entities = self.extractor.extract("المريض يعاني من السكري وارتفاع ضغط الدم")
        self.assertTrue(len(entities) >= 2)


class TestActiveLearning(unittest.TestCase):
    """اختبارات حلقة التعلم الفعّال."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.review_file = os.path.join(self.tmp_dir, "pending.json")
        self.glossary_file = os.path.join(self.tmp_dir, "glossary.json")
        self.mgr = ActiveLearningManager(review_file=self.review_file)

        # إنشاء مسرد اختبار
        self.test_glossary = {
            "terms": {
                "h1": {"term": "Diabetes", "definition": "السكري", "source": "A", "confidence": 0.95},
                "h2": {"term": "Heart Attack", "definition": "نوبة قلبية", "source": "A", "confidence": 0.3},
                "h3": {"term": "Heart Attack", "definition": "احتشاء عضلة القلب", "source": "B", "confidence": 0.9},
                "h4": {"term": "Hypertension", "definition": "ارتفاع ضغط الدم", "source": "A", "confidence": 0.5},
            },
            "metadata": {"total_terms": 4},
        }
        with open(self.glossary_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_glossary, f)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir)

    def test_identify_low_confidence(self):
        """تحديد المصطلحات منخفضة الثقة."""
        n = self.mgr.identify_low_confidence(self.glossary_file, threshold=0.7)
        self.assertEqual(n, 2)  # h2 (0.3) و h4 (0.5)

    def test_identify_duplicates(self):
        """تحديد المكررات."""
        n = self.mgr.identify_duplicates(self.glossary_file)
        self.assertEqual(n, 1)  # h3 (Heart Attack مكرر)

    def test_identify_ambiguous(self):
        """تحديد المبهمة (تعريفات مختلفة لنفس المصطلح)."""
        n = self.mgr.identify_ambiguous(self.glossary_file)
        self.assertEqual(n, 2)  # h2 و h3

    def test_review_flow(self):
        """دورة المراجعة الكاملة."""
        self.mgr.identify_low_confidence(self.glossary_file)
        pending = self.mgr.get_pending()
        self.assertTrue(len(pending) > 0)

        # مراجعة أول عنصر
        item = pending[0]
        self.mgr.review(item.term_hash, action="correct", correction="تعريف مصحح", reviewer="test")

        # التحقق: عنصر أقل في الانتظار
        remaining = self.mgr.get_pending(limit=999)
        self.assertEqual(len(remaining), len(pending) - 1)
        # التحقق: العنصر مُراجَع فعلاً
        reviewed_item = [i for i in self.mgr.pending_items if i.term_hash == item.term_hash]
        self.assertTrue(reviewed_item[0].reviewed)

    def test_apply_corrections(self):
        """تطبيق التصحيحات."""
        self.mgr.identify_low_confidence(self.glossary_file)
        pending = self.mgr.get_pending()
        if pending:
            item = pending[0]
            self.mgr.review(item.term_hash, action="correct", correction="تعريف جديد")
            applied = self.mgr.apply_corrections(self.glossary_file)
            self.assertEqual(applied, 1)

            # التحقق من الملف
            with open(self.glossary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.assertEqual(data["terms"][item.term_hash]["definition"], "تعريف جديد")

    def test_stats(self):
        """إحصائيات المراجعة."""
        self.mgr.identify_low_confidence(self.glossary_file)
        stats = self.mgr.get_stats()
        self.assertEqual(stats["pending"], 2)
        self.assertIn("low_confidence", stats["by_reason"])

    def test_empty_glossary(self):
        """مسرد غير موجود."""
        n = self.mgr.identify_low_confidence("/nonexistent/path.json")
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()