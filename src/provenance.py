import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ProvenanceTracker:
    def __init__(self, db_manager=None):
        self.db = db_manager

    def register_source(self, name, description='', url='', quality_score=0.8):
        if not self.db: return None
        self.db.add_source(name, description, url, quality_score); return name

    def record_term_provenance(self, term_id, source_name, extraction_method='automatic', extractor_version='1.0', original_line='', confidence_basis=''):
        if not self.db: return False
        try:
            conn = self.db.conn; cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS term_provenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT, term_id INTEGER, source_name TEXT,
                extraction_method TEXT, extractor_version TEXT, original_line TEXT,
                confidence_basis TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (term_id) REFERENCES terms(id))''')
            cursor.execute('INSERT INTO term_provenance (term_id, source_name, extraction_method, extractor_version, original_line, confidence_basis) VALUES (?,?,?,?,?,?)',
                (term_id, source_name, extraction_method, extractor_version, original_line, confidence_basis))
            conn.commit(); return True
        except Exception as e: logger.error(f"Provenance error: {e}"); return False

    def get_term_provenance(self, term_id):
        if not self.db: return {}
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM term_provenance WHERE term_id=? ORDER BY timestamp', (term_id,))
            cols = [d[0] for d in cursor.description]; return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except: return []

    def get_term_lineage(self, term_id):
        if not self.db: return []
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT * FROM change_log WHERE term_id=? ORDER BY timestamp', (term_id,))
            cols = [d[0] for d in cursor.description]; return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except: return []

    def get_source_timeline(self, source_name, limit=100):
        if not self.db: return []
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''SELECT tp.*, t.english, t.arabic FROM term_provenance tp JOIN terms t ON tp.term_id=t.id WHERE tp.source_name=? ORDER BY tp.timestamp DESC LIMIT ?''', (source_name, limit))
            cols = [d[0] for d in cursor.description]; return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except: return []

    def get_contribution_report(self):
        if not self.db: return {}
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('SELECT source, COUNT(*) as cnt, AVG(confidence) as avg_conf FROM terms GROUP BY source ORDER BY cnt DESC')
            return [dict(zip(['source','count','avg_confidence'], row)) for row in cursor.fetchall()]
        except: return []

    def get_recent_changes(self, hours=24, limit=100):
        if not self.db: return []
        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''SELECT 'provenance' as type, term_id, source_name as detail, timestamp FROM term_provenance WHERE timestamp >= datetime('now', ?) UNION ALL SELECT 'change' as type, term_id, action as detail, timestamp FROM change_log WHERE timestamp >= datetime('now', ?) ORDER BY timestamp DESC LIMIT ?''', (f'-{hours} hours', f'-{hours} hours', limit))
            cols = [d[0] for d in cursor.description]; return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except: return []

    def diff_snapshots(self, before, after):
        added = [t for t in after if t not in before]; removed = [t for t in before if t not in after]
        return {'added': len(added), 'removed': len(removed), 'before_count': len(before), 'after_count': len(after)}

    def create_snapshot(self, label=''):
        if not self.db: return {}
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM terms'); total = cursor.fetchone()[0]
        cursor.execute('SELECT source, COUNT(*) FROM terms GROUP BY source ORDER BY COUNT(*) DESC LIMIT 10')
        sources = dict(cursor.fetchall())
        return {'timestamp': datetime.now().isoformat(), 'label': label, 'total_terms': total, 'top_sources': sources}