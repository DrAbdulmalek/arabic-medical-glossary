import csv, json, logging, os
from pathlib import Path
from typing import List, Dict, Optional, Callable

logger = logging.getLogger(__name__)

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    HAS_WATCHDOG = True
except ImportError:
    HAS_WATCHDOG = False
    logger.warning("watchdog not installed — directory watching disabled")

class GlossaryFileHandler:
    def __init__(self, callback=None, supported_extensions=None):
        self.callback = callback
        self.extensions = set(supported_extensions or ['.csv', '.json', '.tsv', '.txt'])
        self.processed = set()
    def on_created(self, event):
        if not event.is_directory:
            p = Path(event.src_path)
            if p.suffix.lower() in self.extensions and str(p) not in self.processed:
                logger.info(f"New file: {p}")
                if self.callback: self.callback(str(p))
                self.processed.add(str(p))
    def on_modified(self, event):
        if not event.is_directory:
            p = Path(event.src_path)
            if p.suffix.lower() in self.extensions and str(p) not in self.processed:
                logger.info(f"Modified: {p}")
                if self.callback: self.callback(str(p))
                self.processed.add(str(p))

class AutoIngestion:
    def __init__(self, watch_dir='corpus_sources', db_manager=None, callback=None):
        self.watch_dir = Path(watch_dir); self.db = db_manager; self.callback = callback; self.observer = None
        self.stats = {'processed': 0, 'errors': 0, 'terms_added': 0}

    def start_watching(self):
        if not HAS_WATCHDOG: raise ImportError("watchdog not installed")
        handler = GlossaryFileHandler(callback=self._process_file)
        self.observer = Observer(); self.observer.schedule(handler, str(self.watch_dir), recursive=True)
        self.observer.start(); logger.info(f"Watching: {self.watch_dir}")
    def stop_watching(self):
        if self.observer: self.observer.stop(); self.observer.join(); logger.info("Stopped watching")

    def _process_file(self, file_path):
        p = Path(file_path)
        try:
            data = self._read(p)
            if self.db and data:
                for t in data:
                    en, ar = t.get('english', t.get('en', '')), t.get('arabic', t.get('ar', ''))
                    if en and ar:
                        self.db.add_term(str(en), str(ar), source=p.name, type=t.get('type','term'), confidence=float(t.get('confidence', 0.8)))
                        self.stats['terms_added'] += 1
            self.stats['processed'] += 1
            if self.callback: self.callback(file_path, data)
            return {'status': 'success', 'terms': len(data) if data else 0, 'file': p.name}
        except Exception as e:
            self.stats['errors'] += 1; logger.error(f"Error {p}: {e}")
            return {'status': 'error', 'error': str(e), 'file': p.name}

    def _read(self, path):
        ext = path.suffix.lower()
        if ext == '.csv': return self._read_csv(path)
        elif ext == '.json': return self._read_json(path)
        elif ext == '.tsv': return self._read_tsv(path)
        elif ext == '.txt': return self._read_txt(path)
        return []

    def _read_csv(self, path):
        for enc in ['utf-8-sig', 'utf-8', 'latin-1']:
            try:
                with open(path, 'r', encoding=enc) as f:
                    return list(csv.DictReader(f))
            except: continue
        return []

    def _read_json(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'terms' in data: data = data['terms']
            return data if isinstance(data, list) else [data]

    def _read_tsv(self, path):
        with open(path, 'r', encoding='utf-8-sig') as f: return list(csv.DictReader(f, delimiter='\t'))

    def _read_txt(self, path):
        results = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'): continue
                parts = line.split('\t') if '\t' in line else line.split('|') if '|' in line else line.split(' - ')
                if len(parts) >= 2: results.append({'english': parts[0].strip(), 'arabic': parts[1].strip()})
        return results

    def scan_existing(self):
        results = []
        for ext in ['.csv', '.json', '.tsv', '.txt']:
            for f in self.watch_dir.rglob(f'*{ext}'):
                r = self._process_file(str(f)); results.append(r)
        return results

    def get_stats(self): return dict(self.stats)