"""
اختبارات وحدة دمج المصادر.
"""

import json
import os
import shutil
import tempfile
import unittest

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processors.merge_sources import merge_all_sources


class TestMergeSources(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self._orig_cwd = os.getcwd()

        # إنشاء بنية data/sources داخل tmp_dir
        self.sources_dir = os.path.join(self.tmp_dir, "data", "sources")
        self.merged_dir = os.path.join(self.tmp_dir, "data", "merged")
        os.makedirs(self.sources_dir)

        # التغيير إلى tmp_dir لأن merge_sources يستخدم مسارات نسبية
        os.chdir(self.tmp_dir)

    def tearDown(self):
        os.chdir(self._orig_cwd)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_source(self, name, terms):
        """إنشاء ملف مصدر وهمي"""
        data = {
            "terms": terms,
            "metadata": {"source": name, "created": "2024-01-01T00:00:00"}
        }
        path = os.path.join(self.sources_dir, f"{name}.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def test_merge_empty(self):
        """اختبار دمج بدون مصادر"""
        result = merge_all_sources()
        self.assertEqual(len(result["terms"]), 0)

    def test_merge_deduplication(self):
        """اختبار إلغاء التكرار — نفس المفتاح من مصدرين"""
        term_data = {
            "abc123": {
                "term": "Diabetes",
                "definition": "A chronic disease",
                "source": "MeSH",
                "language": "en",
                "confidence": 0.9
            }
        }
        self._create_source("mesh", term_data)
        # نفس المفتاح
        self._create_source("mesh2", term_data)

        result = merge_all_sources()
        self.assertEqual(len(result["terms"]), 1)

    def test_merge_multiple_sources(self):
        """اختبار دمج عدة مصادر"""
        mesh_terms = {
            "aaa": {"term": "Diabetes", "definition": "Metabolic disease", "source": "MeSH", "language": "en", "confidence": 0.9}
        }
        icd_terms = {
            "bbb": {"term": "Hypertension", "definition": "High BP", "source": "ICD10", "language": "en", "confidence": 0.85}
        }
        self._create_source("mesh", mesh_terms)
        self._create_source("icd10", icd_terms)

        result = merge_all_sources()
        self.assertEqual(len(result["terms"]), 2)
        self.assertEqual(len(result["metadata"]["sources"]), 2)

    def test_merge_by_language(self):
        """اختبار التوزيع حسب اللغة"""
        terms = {
            "a1": {"term": "Diabetes", "definition": "...", "source": "S", "language": "en", "confidence": 0.9},
            "a2": {"term": "السكري", "definition": "...", "source": "S", "language": "ar", "confidence": 0.9},
        }
        self._create_source("test", terms)

        result = merge_all_sources()
        self.assertIn("ar", result["by_language"])
        self.assertIn("en", result["by_language"])
        self.assertEqual(len(result["by_language"]["ar"]), 1)
        self.assertEqual(len(result["by_language"]["en"]), 1)

    def test_merge_output_file_created(self):
        """اختبار إنشاء ملف الدمج"""
        terms = {
            "x": {"term": "X", "definition": "...", "source": "S", "language": "en", "confidence": 0.9}
        }
        self._create_source("test", terms)
        merge_all_sources()

        merged_file = os.path.join(self.merged_dir, "glossary_master.json")
        self.assertTrue(os.path.exists(merged_file))

        with open(merged_file, 'r') as f:
            data = json.load(f)
        self.assertEqual(data["metadata"]["total_terms"], 1)


if __name__ == "__main__":
    unittest.main()