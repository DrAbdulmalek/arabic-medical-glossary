#!/usr/bin/env python3
"""Build SQLite database from data/all_pairs.csv"""
import sys, csv, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db_manager import DatabaseManager
from src.data_cleaner import DataCleaner
from src.config import PROJECT_ROOT

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def build_from_all_pairs(db, cleaner):
    path = PROJECT_ROOT / 'data' / 'all_pairs.csv'
    if not path.exists(): logger.error(f"Not found: {path}"); return 0
    logger.info(f"Reading {path.name}..."); terms = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        for i, row in enumerate(csv.DictReader(f)):
            en, ar = row.get('en', '').strip(), row.get('ar', '').strip()
            if not en or not ar: continue
            en_c, ar_c = cleaner.clean_english(en), cleaner.clean_arabic(ar)
            if not en_c or not ar_c: continue
            terms.append({'english': en_c, 'arabic': ar_c, 'source': row.get('source', 'unknown'), 'type': cleaner.normalize_type(row.get('type', 'term')), 'section': row.get('section', ''), 'confidence': cleaner.normalize_confidence(row.get('confidence', 0.8)), 'hash': row.get('hash', cleaner.generate_hash(en_c, ar_c))})
            if len(terms) % 50000 == 0: logger.info(f"  {len(terms)} terms...")
    logger.info(f"Inserting {len(terms)} terms..."); return db.add_terms_bulk(terms)

def main():
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--db'); p.add_argument('--skip-all-pairs', action='store_true'); p.add_argument('--force', action='store_true')
    args = p.parse_args()
    from src.config import DB_PATH; db_path = args.db or str(DB_PATH)
    if args.force and Path(db_path).exists(): Path(db_path).unlink()
    db = DatabaseManager(db_path=db_path); cleaner = DataCleaner()
    if not args.skip_all_pairs:
        count = build_from_all_pairs(db, cleaner); logger.info(f"Imported {count} terms")
    logger.info(f"Total: {db.get_total_count()} terms, {len(db.get_all_sources())} sources"); db.close()

if __name__ == '__main__': main()