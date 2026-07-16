"""
اختبارات شاملة لوحدة BaseCollector.
"""

import json
import os
import shutil
import unittest
import tempfile
from datetime import datetime

# نحتاج لتعديل مسار العمل ليشمل المشروع
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from collectors.base import BaseCollector, TermEntry


class MockCollector(BaseCollector):
    """مجمع وهمي للاختبار"""
    def __init__(self, tmp_dir, config=None):
        self._test_dir = tmp_dir
        # تجاوز المسارات الافتراضية
        super().__init__("TestSource", "https://test.example.com", config)
        # إعادة توجيه المسارات إلى مجلد مؤقت
        self.data_dir = os.path.join(tmp_dir, "sources")
        self.progress_dir = os.path.join(tmp_dir, "progress")
        self.log_dir = os.path.join(tmp_dir, "logs")
        self.source_file = os.path.join(self.data_dir, "testsource.json")
        self.progress_file = os.path.join(self.progress_dir, "state.json")
        for d in [self.data_dir, self.progress_dir, self.log_dir]:
            os.makedirs(d, exist_ok=True)

    def collect(self) -> int:
        entries = [
            TermEntry(term="Diabetes", definition="A chronic metabolic disease", source="TestSource", language="en", confidence=0.95),
            TermEntry(term="Hypertension", definition="High blood pressure", source="TestSource", language="en", confidence=0.9),
            TermEntry(term="السكري", definition="مرض أيضي مزمن", source="TestSource", language="ar", confidence=0.85),
        ]
        count = 0
        for e in entries:
            if self.add_term(e):
                count += 1
        return count


class TestBaseCollector(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_add_term_new(self):
        """اختبار إضافة مصطلح جديد"""
        collector = MockCollector(self.tmp_dir)
        entry = TermEntry(term="Test", definition="A test term", source="Test", language="en")
        result = collector.add_term(entry)
        self.assertTrue(result)

        data = collector.load_source_data()
        self.assertEqual(len(data["terms"]), 1)

    def test_add_term_duplicate(self):
        """اختبار عدم التكرار"""
        collector = MockCollector(self.tmp_dir)
        entry = TermEntry(term="Test", definition="A test term", source="Test", language="en")
        collector.add_term(entry)
        result = collector.add_term(entry)
        self.assertFalse(result)

        data = collector.load_source_data()
        self.assertEqual(len(data["terms"]), 1)

    def test_add_term_higher_confidence(self):
        """اختبار تحديث بثقة أعلى"""
        collector = MockCollector(self.tmp_dir)
        entry1 = TermEntry(term="Test", definition="Old def", source="Test", language="en", confidence=0.5)
        entry2 = TermEntry(term="Test", definition="New def", source="Test", language="en", confidence=0.9)

        collector.add_term(entry1)
        result = collector.add_term(entry2)

        self.assertTrue(result)
        data = collector.load_source_data()
        # يجب أن يكون التعريف الجديد
        for term_data in data["terms"].values():
            if term_data["term"] == "Test":
                self.assertEqual(term_data["definition"], "New def")
                self.assertEqual(term_data["confidence"], 0.9)

    def test_batch_buffering(self):
        """اختبار حفظ دفعي — يجب ألا يحفظ لكل مصطلح"""
        collector = MockCollector(self.tmp_dir)
        collector._buffer_size = 100  # عدم الحفظ حتى 100

        for i in range(10):
            entry = TermEntry(
                term=f"Term{i}", definition=f"Definition {i}",
                source="Test", language="en"
            )
            collector.add_term(entry)

        # لا يجب أن يكون الملف موجوداً بعد (أقل من buffer_size)
        # لكن flush يجب أن يحفظها
        collector.flush()
        data = collector.load_source_data()
        self.assertEqual(len(data["terms"]), 10)

    def test_run_full_cycle(self):
        """اختبار دورة كاملة لـ run()"""
        collector = MockCollector(self.tmp_dir)
        result = collector.run()

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["new_terms"], 3)

    def test_term_entry_hash_uniqueness(self):
        """اختبار تميز المفتاح الفريد"""
        e1 = TermEntry(term="Diabetes", definition="...", source="A", language="en")
        e2 = TermEntry(term="Diabetes", definition="...", source="B", language="en")
        e3 = TermEntry(term="Diabetes", definition="...", source="A", language="ar")

        self.assertNotEqual(e1.get_hash(), e2.get_hash())
        self.assertNotEqual(e1.get_hash(), e3.get_hash())
        self.assertNotEqual(e2.get_hash(), e3.get_hash())

    def test_term_entry_default_values(self):
        """اختبار القيم الافتراضية لـ TermEntry"""
        entry = TermEntry(term="Test", definition="Definition", source="S", language="en")
        self.assertEqual(entry.confidence, 1.0)
        self.assertEqual(entry.tags, [])
        self.assertIsNotNone(entry.date_added)

    def test_progress_tracking(self):
        """اختبار تتبع التقدم"""
        collector = MockCollector(self.tmp_dir)
        collector.run()

        progress = collector.load_progress()
        self.assertIn("TestSource", progress["sources"])
        self.assertEqual(progress["sources"]["TestSource"]["status"], "completed")
        self.assertEqual(progress["sources"]["TestSource"]["terms_collected"], 3)


if __name__ == "__main__":
    unittest.main()