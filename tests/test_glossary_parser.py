"""
Tests for glossary parser.
"""

import unittest
from processors.glossary_parser import parse_glossary_from_text, _detect_language


class TestGlossaryParser(unittest.TestCase):

    def test_pattern_colon_arabic(self):
        text = "السكري: مرض مزمن يؤثر على مستوى السكر في الدم"
        results = parse_glossary_from_text(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].term, "السكري")
        self.assertEqual(results[0].language, "ar")

    def test_pattern_colon_english(self):
        text = "Diabetes: A chronic disease affecting blood sugar levels"
        results = parse_glossary_from_text(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].term, "Diabetes")
        self.assertEqual(results[0].language, "en")

    def test_pattern_numbered(self):
        text = "1. Hypertension - High blood pressure condition"
        results = parse_glossary_from_text(text)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].term, "Hypertension")

    def test_detect_language_arabic(self):
        self.assertEqual(_detect_language("السكري"), "ar")

    def test_detect_language_english(self):
        self.assertEqual(_detect_language("Diabetes"), "en")


if __name__ == "__main__":
    unittest.main()
