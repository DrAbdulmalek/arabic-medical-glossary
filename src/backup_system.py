import sqlite3, shutil, zipfile, json, logging, hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class BackupManager:
    def __init__(self, backup_dir='backups', db_path='medical_glossary.db', data_dirs=None, max_backups=10):
        self.backup_dir = Path(backup_dir); self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = Path(db_path); self.data_dirs = [Path(d) for d in (data_dirs or [])]; self.max_backups = max_backups

    def create_backup(self, label='', include_db=True, include_data=True, include_config=True):
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        name = f"glossary_backup_{ts}{'_'+label if label else ''}.zip"
        path = self.backup_dir / name
        manifest = {'timestamp': ts, 'label': label, 'created': datetime.now().isoformat(), 'files': []}
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zf:
            if include_db and self.db_path.exists():
                zf.write(self.db_path, self.db_path.name)
                h = hashlib.sha256(self.db_path.read_bytes()).hexdigest()
                manifest['files'].append({'name': self.db_path.name, 'size': self.db_path.stat().st_size, 'sha256': h})
            if include_data:
                for d in self.data_dirs:
                    if d.exists():
                        for f in d.rglob('*'):
                            if f.is_file():
                                arc = str(f.relative_to(d.parent))
                                zf.write(f, arc); h = hashlib.sha256(f.read_bytes()).hexdigest()
                                manifest['files'].append({'name': arc, 'size': f.stat().st_size, 'sha256': h})
            zf.writestr('manifest.json', json.dumps(manifest, indent=2, ensure_ascii=False))
        logger.info(f"Backup created: {path}"); return str(path)

    def create_db_backup(self):
        if not self.db_path.exists(): raise FileNotFoundError(f"DB not found: {self.db_path}")
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out = self.backup_dir / f"db_backup_{ts}.db"
        src = sqlite3.connect(str(self.db_path)); dst = sqlite3.connect(str(out))
        src.backup(dst); dst.close(); src.close()
        logger.info(f"DB backup: {out}"); return str(out)

    def restore_backup(self, backup_path, target_dir='.'):
        bp = Path(backup_path); td = Path(target_dir)
        with zipfile.ZipFile(bp, 'r') as zf:
            zf.extractall(td)
        logger.info(f"Restored from {bp}"); return {'restored': [f.filename for f in zipfile.ZipFile(bp).namelist()]}

    def list_backups(self):
        results = []
        for f in sorted(self.backup_dir.glob('glossary_backup_*.zip'), reverse=True):
            try:
                with zipfile.ZipFile(f, 'r') as zf:
                    m = json.loads(zf.read('manifest.json'))
                    results.append({'path': str(f), 'timestamp': m.get('timestamp',''), 'label': m.get('label',''), 'files': len(m.get('files',[])), 'size_mb': f.stat().st_size/1048576})
            except: pass
        return results

    def get_latest_backup(self):
        b = self.list_backups(); return b[0]['path'] if b else None

    def delete_backup(self, backup_path):
        p = Path(backup_path)
        if p.exists(): p.unlink(); return True
        return False

    def rotate_backups(self):
        backups = sorted(self.backup_dir.glob('glossary_backup_*.zip'), key=lambda f: f.stat().st_mtime)
        deleted = []
        while len(backups) > self.max_backups:
            b = backups.pop(0); b.unlink(); deleted.append(str(b))
        if deleted: logger.info(f"Rotated {len(deleted)} old backups")
        return deleted

    def verify_backup(self, backup_path):
        bp = Path(backup_path); result = {'path': str(bp), 'valid_zip': False, 'manifest_ok': False, 'files_ok': 0, 'files_total': 0}
        try:
            with zipfile.ZipFile(bp, 'r') as zf:
                zf.testzip(); result['valid_zip'] = True
                m = json.loads(zf.read('manifest.json')); result['manifest_ok'] = True; result['files_total'] = len(m.get('files',[]))
                for fi in m.get('files',[]):
                    try:
                        data = zf.read(fi['name'])
                        if hashlib.sha256(data).hexdigest() == fi.get('sha256',''): result['files_ok'] += 1
                    except: pass
        except Exception as e: result['error'] = str(e)
        return result

    def get_backup_size(self, backup_path): return Path(backup_path).stat().st_size
    def schedule_backup(self, interval_hours=24): return f"0 {datetime.now().hour} * * *  # Daily at {datetime.now().strftime('%H:%M')}"