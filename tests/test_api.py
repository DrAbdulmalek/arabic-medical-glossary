"""
اختبارات شاملة لـ REST API — Medical Glossary.
يستخدم TestClient من FastAPI (بدون تشغيل خادم فعلي).
"""

import json
import os
import sys
import unittest

# ضبط مسار العمل
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from api.main import app


class TestHealthEndpoints(unittest.TestCase):
    """اختبارات نقاط الصحة والمعلومات الأساسية."""

    def setUp(self):
        self.client = TestClient(app)

    def test_root(self):
        """اختبار نقطة البداية."""
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("total_terms", data)
        self.assertGreater(data["total_terms"], 0)
        self.assertEqual(data["version"], "1.0.0-rc1")

    def test_health_check(self):
        """اختبار فحص الصحة."""
        r = self.client.get("/health")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["status"], "ok")
        self.assertGreater(data["total_terms"], 0)


class TestSearchEndpoint(unittest.TestCase):
    """اختبارات البحث."""

    def setUp(self):
        self.client = TestClient(app)

    def test_search_english(self):
        """بحث عن مصطلح إنجليزي."""
        r = self.client.get("/search?q=diabetes")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreater(data["total"], 0)
        self.assertGreater(len(data["results"]), 0)
        self.assertEqual(data["query"], "diabetes")

    def test_search_arabic(self):
        """بحث عن مصطلح عربي."""
        r = self.client.get("/search?q=%D8%B3%D9%83%D8%B1%D9%8A")  # سكري
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreater(data["total"], 0)

    def test_search_with_language_filter(self):
        """بحث مع تصفية اللغة."""
        r = self.client.get("/search?q=diabetes&language=en")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for term in data["results"]:
            self.assertEqual(term["language"], "en")

    def test_search_pagination(self):
        """اختبار الـ Pagination."""
        r1 = self.client.get("/search?q=drug&limit=5&offset=0")
        r2 = self.client.get("/search?q=drug&limit=5&offset=5")
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        d1, d2 = r1.json(), r2.json()
        self.assertEqual(len(d1["results"]), min(5, d1["total"]))
        self.assertGreaterEqual(d1["total"], 0)

    def test_search_empty_query(self):
        """رفض بحث فارغ."""
        r = self.client.get("/search?q=")
        self.assertEqual(r.status_code, 422)

    def test_search_post(self):
        """بحث متقدم عبر POST."""
        payload = {
            "query": "blood",
            "language": "en",
            "limit": 5,
        }
        r = self.client.post("/search", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreater(data["total"], 0)

    def test_search_not_found(self):
        """بحث عن مصطلح غير موجود."""
        r = self.client.get("/search?q=xyznonexistent12345")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["results"]), 0)


class TestBrowseEndpoints(unittest.TestCase):
    """اختبارات التصفح."""

    def setUp(self):
        self.client = TestClient(app)

    def test_browse_all(self):
        """تصفح جميع المصطلحات."""
        r = self.client.get("/terms?limit=5")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreaterEqual(data["total"], 0)
        self.assertLessEqual(len(data["results"]), 5)

    def test_browse_by_language(self):
        """تصفح حسب اللغة."""
        r = self.client.get("/terms?language=ar&limit=3")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for term in data["results"]:
            self.assertEqual(term["language"], "ar")

    def test_browse_by_source(self):
        """تصفح حسب المصدر."""
        r = self.client.get("/terms?source=CustomGlossaries&limit=3")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        for term in data["results"]:
            self.assertEqual(term["source"], "CustomGlossaries")

    def test_get_specific_term(self):
        """جلب مصطلح محدد."""
        # أولاً نبحث عن مصطلح موجود
        r = self.client.get("/terms?limit=1")
        if r.json()["results"]:
            first_term = r.json()["results"][0]["term"]
            r2 = self.client.get(f"/terms/{first_term}")
            self.assertEqual(r2.status_code, 200)
            self.assertGreater(len(r2.json()), 0)

    def test_get_nonexistent_term(self):
        """جلب مصطلح غير موجود — يجب أن يُرجع 404."""
        r = self.client.get("/terms/xyznonexistent12345")
        self.assertEqual(r.status_code, 404)


class TestStatsEndpoints(unittest.TestCase):
    """اختبارات الإحصائيات."""

    def setUp(self):
        self.client = TestClient(app)

    def test_stats(self):
        """اختبار نقطة الإحصائيات."""
        r = self.client.get("/stats")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertGreater(data["total_terms"], 0)
        self.assertIn("by_language", data)
        self.assertIn("by_source", data)

    def test_sources_list(self):
        """اختبار قائمة المصادر."""
        r = self.client.get("/sources")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIsInstance(data, list)


class TestRandomEndpoint(unittest.TestCase):
    """اختبار المصطلحات العشوائية."""

    def setUp(self):
        self.client = TestClient(app)

    def test_random_terms(self):
        """اختبار جلب مصطلحات عشوائية."""
        r = self.client.get("/random?count=3")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data), 3)

    def test_random_with_language(self):
        """مصطلحات عشوائية بلغة محددة."""
        r = self.client.get("/random?count=2&language=ar")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data), 2)
        for term in data:
            self.assertEqual(term["language"], "ar")


class TestReloadEndpoint(unittest.TestCase):
    """اختبار إعادة التحميل."""

    def setUp(self):
        self.client = TestClient(app)

    def test_reload(self):
        """اختبار إعادة تحميل البيانات."""
        r = self.client.post("/reload")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("total_terms", data)
        self.assertGreater(data["total_terms"], 0)


class TestOpenAPISchema(unittest.TestCase):
    """اختبار توثيق OpenAPI."""

    def setUp(self):
        self.client = TestClient(app)

    def test_openapi_json(self):
        """اختبار نقطة OpenAPI JSON."""
        r = self.client.get("/openapi.json")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["info"]["title"], "Arabic-English Medical Glossary API")
        self.assertIn("/search", data["paths"])
        self.assertIn("/terms", data["paths"])
        self.assertIn("/stats", data["paths"])


if __name__ == "__main__":
    unittest.main()