#!/usr/bin/env python3
import sys, unittest, tempfile, os, shutil
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_cleaner import DataCleaner
from src.db_manager import DatabaseManager
from src.source_merger import SourceMerger
from src.quality_checker import QualityChecker
from src.exporter import MultiExporter
from src.statistics import StatisticsGenerator
from src.backup_system import BackupManager
from src.plugin_manager import PluginManager, BuiltinCSVPlugin, BuiltinJSONPlugin

class TestDataCleaner(unittest.TestCase):
    def setUp(self): self.cleaner = DataCleaner()
    def test_clean_english_basic(self): self.assertEqual(self.cleaner.clean_english("  Hello World  "), "hello world")
    def test_clean_english_special(self): self.assertEqual(self.cleaner.clean_english("Blood Pressure (BP)"), "blood pressure (bp)")
    def test_clean_arabic_tashkeel(self):
        r = self.cleaner.clean_arabic("اَلْقَلْبُ")
        self.assertNotIn('\u064B', r); self.assertNotIn('\u064E', r)
    def test_clean_arabic_html(self): self.assertNotIn('<', self.cleaner.clean_arabic("<b>قلب</b>"))
    def test_normalize_confidence_str_high(self): self.assertAlmostEqual(self.cleaner.normalize_confidence('high'), 1.0)
    def test_normalize_confidence_str_very_high(self): self.assertAlmostEqual(self.cleaner.normalize_confidence('very_high'), 0.95)
    def test_normalize_confidence_str_medium(self): self.assertAlmostEqual(self.cleaner.normalize_confidence('medium'), 0.7)
    def test_normalize_confidence_str_low(self): self.assertAlmostEqual(self.cleaner.normalize_confidence('low'), 0.5)
    def test_normalize_confidence_float(self): self.assertAlmostEqual(self.cleaner.normalize_confidence(0.85), 0.85)
    def test_generate_hash_consistent(self):
        h1 = self.cleaner.generate_hash("heart", "قلب"); h2 = self.cleaner.generate_hash("heart", "قلب")
        self.assertEqual(h1, h2)
    def test_generate_hash_case_insensitive(self):
        self.assertEqual(self.cleaner.generate_hash("heart", "قلب"), self.cleaner.generate_hash("Heart", "قلب"))
    def test_validate_english_valid(self): v, _ = self.cleaner.validate_english("myocardial infarction"); self.assertTrue(v)
    def test_validate_english_empty(self): v, _ = self.cleaner.validate_english(""); self.assertFalse(v)
    def test_validate_arabic_valid(self): v, _ = self.cleaner.validate_arabic("احتشاء عضلة القلب"); self.assertTrue(v)
    def test_deduplicate_terms(self):
        terms = [
            {'english': 'heart', 'arabic': 'قلب', 'confidence': 0.7, 'hash': 'abc'},
            {'english': 'heart', 'arabic': 'قلب', 'confidence': 0.9, 'hash': 'abc'},
            {'english': 'liver', 'arabic': 'كبد', 'confidence': 0.8, 'hash': 'def'}
        ]
        result = self.cleaner.deduplicate_terms(terms)
        self.assertEqual(len(result), 2)
        self.assertAlmostEqual(result[0]['confidence'], 0.9)
    def test_remove_markdown(self): self.assertEqual(self.cleaner.remove_markdown("**bold**"), "bold")

class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.fd, self.db_path = tempfile.mkstemp(suffix='.db'); os.close(self.fd)
        self.db = DatabaseManager(db_path=self.db_path)
    def tearDown(self):
        self.db.close(); os.unlink(self.db_path)
    def test_add_get(self):
        tid = self.db.add_term("heart", "قلب", source="test", hash='x0')
        t = self.db.get_term(tid)
        self.assertIsNotNone(t); self.assertEqual(t['english'], 'heart')
    def test_duplicate_ignored(self):
        self.db.add_term("heart", "قلب", source="test", hash='x1')
        try:
            self.db.add_term("heart", "قلب", source="test", hash='x1')
        except Exception:
            pass
        self.assertEqual(self.db.get_total_count(), 1)
    def test_search_english(self):
        self.db.add_term("myocardial infarction", "احتشاء عضلة القلب", source="test", hash='x2')
        self.assertEqual(len(self.db.search_by_english("myocardial")), 1)
    def test_search_arabic(self):
        self.db.add_term("heart", "قلب", source="test", hash='x3')
        self.assertEqual(len(self.db.search_by_arabic("قلب")), 1)
    def test_fulltext_search(self):
        self.db.add_term("blood pressure", "ضغط الدم", source="test", hash='a')
        self.db.add_term("blood sugar", "سكر الدم", source="test", hash='b')
        self.assertEqual(len(self.db.fulltext_search("blood")), 2)
    def test_update_term(self):
        tid = self.db.add_term("heart", "قلب", source="test", confidence=0.5, hash='c')
        self.db.update_term(tid, confidence=0.95); self.assertAlmostEqual(self.db.get_term(tid)['confidence'], 0.95)
    def test_delete_term(self):
        tid = self.db.add_term("heart", "قلب", source="test", hash='d')
        self.db.delete_term(tid); self.assertIsNone(self.db.get_term(tid))
    def test_verify_term(self):
        tid = self.db.add_term("heart", "قلب", source="test", hash='e')
        self.db.verify_term(tid, 'verified'); self.assertEqual(self.db.get_term(tid)['validation_status'], 'verified')
    def test_add_source(self):
        self.db.add_source("src1", "desc", "http://x.com", 0.9)
        sources = self.db.get_all_sources()
        self.assertTrue(any(s['name'] == 'src1' for s in sources))
    def test_bulk_insert(self):
        terms = [{'english': f'term{i}', 'arabic': f'مصطلح{i}', 'source': 'test', 'type': 'term', 'section': '', 'confidence': 0.8, 'hash': f'h{i}'} for i in range(100)]
        self.assertEqual(self.db.add_terms_bulk(terms), 100)
    def test_term_history(self):
        tid = self.db.add_term("heart", "قلب", source="test", confidence=0.5, hash='f')
        self.db.update_term(tid, confidence=0.9)
        self.assertEqual(len(self.db.get_term_history(tid)), 1)

class TestQualityChecker(unittest.TestCase):
    def setUp(self): self.checker = QualityChecker()
    def test_empty_fields(self):
        issues = self.checker.check_empty_fields([{'english': 'heart', 'arabic': 'قلب'}, {'english': '', 'arabic': 'كبد'}])
        self.assertEqual(len(issues), 1)
    def test_confidence_range(self):
        issues = self.checker.check_confidence_range([{'english': 'a', 'arabic': 'أ', 'confidence': 1.5}, {'english': 'b', 'arabic': 'ب', 'confidence': 0.8}])
        self.assertEqual(len(issues), 1)
    def test_quality_score(self):
        score = self.checker.get_quality_score([{'english': 'heart', 'arabic': 'قلب', 'confidence': 0.95, 'type': 'term', 'source': 'test', 'section': 'cardiology', 'validation_status': 'verified'}])
        self.assertGreater(score, 0); self.assertLessEqual(score, 100)
    def test_check_duplicates(self):
        dupes = self.checker.check_duplicates([
            {'english': 'heart', 'arabic': 'قلب'},
            {'english': 'heart', 'arabic': 'قلب'},
            {'english': 'liver', 'arabic': 'كبد'}
        ])
        self.assertEqual(len(dupes), 1)

class TestSourceMerger(unittest.TestCase):
    def test_deduplicate(self):
        terms = [
            {'english': 'heart', 'arabic': 'قلب', 'confidence': 0.7, 'source': 'a'},
            {'english': 'heart', 'arabic': 'قلب', 'confidence': 0.9, 'source': 'b'}
        ]
        result = SourceMerger().deduplicate(terms)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]['confidence'], 0.9)
    def test_merge_report(self):
        merger = SourceMerger()
        merger.deduplicate([
            {'english': 'heart', 'arabic': 'قلب', 'confidence': 0.7, 'source': 'a'},
            {'english': 'heart', 'arabic': 'قلب', 'confidence': 0.9, 'source': 'b'}
        ])
        report = merger.get_merge_report()
        self.assertEqual(report['conflicts_resolved'], 1)

class TestExporter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.exp = MultiExporter()
        self.data = [{'english': 'heart', 'arabic': 'قلب', 'source': 'test', 'confidence': 0.9}]
    def tearDown(self): shutil.rmtree(self.tmp)
    def test_csv(self): self.assertTrue(self.exp.export_to_csv(Path(self.tmp) / 't.csv', terms=self.data).exists())
    def test_json(self): self.assertTrue(self.exp.export_to_json(Path(self.tmp) / 't.json', terms=self.data).exists())
    def test_jsonl(self): self.assertTrue(self.exp.export_to_jsonl(Path(self.tmp) / 't.jsonl', terms=self.data).exists())
    def test_tsv(self): self.assertTrue(self.exp.export_to_tsv(Path(self.tmp) / 't.tsv', terms=self.data).exists())
    def test_round_trip(self):
        p = self.exp.export_to_csv(Path(self.tmp) / 'rt.csv', terms=self.data)
        df = pd.read_csv(p)
        self.assertEqual(len(df), 1); self.assertIn('heart', df.iloc[0].values)
    def test_export_log(self):
        self.exp.export_to_csv(Path(self.tmp) / 'log.csv', terms=self.data)
        self.assertTrue(len(self.exp.get_export_log()) > 0)

class TestStatistics(unittest.TestCase):
    def setUp(self):
        self.fd, self.db_path = tempfile.mkstemp(suffix='.db'); os.close(self.fd)
        self.db = DatabaseManager(db_path=self.db_path)
        self.db.add_term("heart", "قلب", source="a", hash='s1', confidence=0.9, type='term')
    def tearDown(self):
        self.db.close(); os.unlink(self.db_path)
    def test_overview(self):
        gen = StatisticsGenerator(db_manager=self.db)
        stats = gen.get_overview()
        self.assertEqual(stats['total_terms'], 1)
    def test_empty(self):
        fd2, db_path2 = tempfile.mkstemp(suffix='.db'); os.close(fd2)
        db2 = DatabaseManager(db_path=db_path2)
        self.assertEqual(StatisticsGenerator(db_manager=db2).get_overview()['total_terms'], 0)
        db2.close(); os.unlink(db_path2)
    def test_report(self):
        r = StatisticsGenerator(db_manager=self.db).generate_text_report()
        self.assertIn('1', r)

class TestBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.db_fd, self.db_file = tempfile.mkstemp(suffix='.db', dir=self.tmp)
        os.close(self.db_fd)
        self.mgr = BackupManager(backup_dir=self.tmp, db_path=self.db_file, max_backups=3)
    def tearDown(self): shutil.rmtree(self.tmp)
    def test_create_list(self):
        p = self.mgr.create_backup(label='test')
        self.assertTrue(Path(p).exists())
        self.assertEqual(len(self.mgr.list_backups()), 1)

class TestPluginManager(unittest.TestCase):
    def test_register_list(self):
        pm = PluginManager(plugins_dir=tempfile.mkdtemp())
        pm.register_builtin('csv', BuiltinCSVPlugin); pm.register_builtin('json', BuiltinJSONPlugin)
        self.assertEqual(len(pm.list_plugins()), 2)
    def test_csv_extract(self):
        import tempfile as tf
        p = tf.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8-sig')
        p.write('en,ar,source\nheart,قلب,test\nliver,كبد,test\n'); p.close()
        data = BuiltinCSVPlugin.extract(p.name); os.unlink(p.name)
        self.assertIsInstance(data, list)
    def test_template(self):
        pm = PluginManager(plugins_dir=tempfile.mkdtemp()); p = pm.create_plugin_template('test')
        self.assertTrue(Path(p).exists())
    def test_auto_detect(self):
        pm = PluginManager(); pm.register_builtin('csv', BuiltinCSVPlugin)
        self.assertEqual(pm.auto_detect_plugin('test.CSV'), 'csv')

if __name__ == '__main__': unittest.main()