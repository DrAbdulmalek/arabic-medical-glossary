"""
اختبارات وحدة استخراج النصوص.
"""

import os
import shutil
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processors.text_extractor import extract_text_from_file


class TestTextExtractor(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_extract_txt(self):
        """اختبار استخراج من ملف TXT"""
        path = os.path.join(self.tmp_dir, "test.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write("Diabetes: A chronic metabolic disease\n")

        result = extract_text_from_file(path)
        self.assertIn("Diabetes", result)

    def test_extract_txt_arabic(self):
        """اختبار استخراج نص عربي"""
        path = os.path.join(self.tmp_dir, "ar.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write("السكري: مرض مزمن يؤثر على مستوى السكر")

        result = extract_text_from_file(path)
        self.assertIn("السكري", result)

    def test_extract_nonexistent_file(self):
        """اختبار ملف غير موجود"""
        result = extract_text_from_file("/nonexistent/file.txt")
        self.assertIsNone(result)

    def test_extract_unsupported_format(self):
        """اختبار صيغة غير مدعومة — يجب أن يستخدم fallback"""
        path = os.path.join(self.tmp_dir, "test.xyz")
        with open(path, 'w', encoding='utf-8') as f:
            f.write("Some text content here")

        result = extract_text_from_file(path)
        # fallback يحاول القراءة بأترمة متعددة
        self.assertIsNotNone(result)
        self.assertIn("Some", result)

    def test_extract_empty_file(self):
        """اختبار ملف فارغ"""
        path = os.path.join(self.tmp_dir, "empty.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write("")

        result = extract_text_from_file(path)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()