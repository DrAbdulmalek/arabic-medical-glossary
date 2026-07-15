#!/usr/bin/env python3
"""Arabic Medical Glossary CLI"""
import sys, argparse, logging, csv, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db_manager import DatabaseManager
from src.data_cleaner import DataCleaner
from src.source_merger import SourceMerger
from src.exporter import MultiExporter
from src.quality_checker import QualityChecker
from src.statistics import StatisticsGenerator
from src.backup_system import BackupManager
from src.plugin_manager import PluginManager, BuiltinCSVPlugin, BuiltinJSONPlugin

def cmd_search(args):
    db = DatabaseManager()
    if args.fulltext: results = db.fulltext_search(args.query, limit=args.limit, category=args.category)
    else: results = db.search(args.query, limit=args.limit, category=args.category, source=args.source, type=args.type)
    if results:
        print(f"{'ID':<6}{'English':<40}{'Arabic':<40}{'Source':<20}{'Conf':<5}"); print("-"*120)
        for r in results: print(f"{r.get('id',''):<6}{str(r.get('english',''))[:39]:<40}{str(r.get('arabic',''))[:39]:<40}{str(r.get('source',''))[:19]:<20}{str(r.get('confidence','')):<5}")
        print(f"\nTotal: {len(results)}")
    else: print("No results found.")
    db.close()

def cmd_import(args):
    db = DatabaseManager(); cleaner = DataCleaner(); path = Path(args.file); count = 0
    if path.suffix == '.csv':
        with open(path, 'r', encoding='utf-8-sig') as f:
            terms = []
            for row in csv.DictReader(f):
                en, ar = row.get('en', row.get('english', '')), row.get('ar', row.get('arabic', ''))
                if not en or not ar: continue
                en, ar = cleaner.clean_english(en), cleaner.clean_arabic(ar)
                terms.append({'english': en, 'arabic': ar, 'source': row.get('source', path.name), 'type': cleaner.normalize_type(row.get('type', 'term')), 'section': row.get('section', ''), 'confidence': cleaner.normalize_confidence(row.get('confidence', 0.8)), 'hash': row.get('hash', cleaner.generate_hash(en, ar))})
            count = db.add_terms_bulk(terms)
    elif path.suffix == '.json':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, dict) and 'terms' in data: data = data['terms']
            terms = []
            for row in data:
                en, ar = row.get('en', row.get('english', '')), row.get('ar', row.get('arabic', ''))
                if not en or not ar: continue
                en, ar = cleaner.clean_english(en), cleaner.clean_arabic(ar)
                terms.append({'english': en, 'arabic': ar, 'source': row.get('source', path.name), 'type': cleaner.normalize_type(row.get('type', 'term')), 'section': row.get('section', ''), 'confidence': cleaner.normalize_confidence(row.get('confidence', 0.8)), 'hash': row.get('hash', cleaner.generate_hash(en, ar))})
            count = db.add_terms_bulk(terms)
    print(f"Imported {count} terms from {path.name}"); db.close()

def cmd_export(args):
    db = DatabaseManager(); cursor = db.conn.cursor()
    cursor.execute("SELECT * FROM terms LIMIT ?", (args.limit,))
    cols = [d[0] for d in cursor.description]; data = [dict(zip(cols, row)) for row in cursor.fetchall()]; db.close()
    exporter = MultiExporter(output_dir=args.output or 'exports'); fmt = args.format.lower()
    if fmt == 'csv': path = exporter.export_to_csv(data, args.filename or 'export.csv')
    elif fmt == 'json': path = exporter.export_to_json(data, args.filename or 'export.json')
    elif fmt == 'sqlite': path = exporter.export_to_sqlite(data, args.filename or 'export.db')
    elif fmt == 'all': paths = exporter.export_all_formats(data, args.filename or 'glossary'); [print(f"  {k}: {v}") for k,v in paths.items()]; return
    else: print(f"Unknown: {fmt}. Use: csv, json, sqlite, all"); return
    print(f"Exported to: {path}")

def cmd_stats(args):
    db = DatabaseManager(); gen = StatisticsGenerator(db_manager=db); print(gen.generate_text_report(format='markdown')); db.close()

def cmd_quality(args):
    db = DatabaseManager(); checker = QualityChecker(db_manager=db); results = checker.check_all()
    report = checker.generate_quality_report(results); print(report)
    if args.output: Path(args.output).write_text(report, encoding='utf-8'); print(f"Saved to: {args.output}")
    db.close()

def cmd_backup(args):
    mgr = BackupManager()
    if args.action == 'create': print(f"Backup: {mgr.create_backup(label=args.label)}")
    elif args.action == 'list':
        for b in mgr.list_backups(): print(f"  {b['timestamp']} | {b['label']} | {b['size_mb']:.1f} MB | {b['files']} files")
    elif args.action == 'restore': print(f"Restored {len(mgr.restore_backup(args.path)['restored'])} files")
    elif args.action == 'rotate': print(f"Deleted {len(mgr.rotate_backups())} old backups")

def cmd_merge(args):
    merger = SourceMerger(strategy=args.strategy)
    if args.directory:
        result = merger.smart_merge_glossary_directory(args.directory); print(f"Merged {len(result)} terms")
        if args.output: result.to_csv(args.output, index=False, encoding='utf-8-sig'); print(f"Saved: {args.output}")
    elif args.files:
        result = merger.merge_csv_files([str(Path(f).resolve()) for f in args.files]); print(f"Merged {len(result)} terms")

def cmd_plugins(args):
    pm = PluginManager(); pm.register_builtin('csv', BuiltinCSVPlugin); pm.register_builtin('json', BuiltinJSONPlugin)
    if args.action == 'list':
        for p in pm.list_plugins(): print(f"  {p['name']} | {p['description']} | {', '.join(p['extensions'])} | {p['source']}")
    elif args.action == 'create': print(f"Template: {pm.create_plugin_template(args.name)}")

def main():
    parser = argparse.ArgumentParser(description='Arabic Medical Glossary CLI', formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command')
    p = sub.add_parser('search'); p.add_argument('query'); p.add_argument('--fulltext', action='store_true'); p.add_argument('--limit', type=int, default=50); p.add_argument('--category'); p.add_argument('--source'); p.add_argument('--type'); p.set_defaults(func=cmd_search)
    p = sub.add_parser('import'); p.add_argument('file'); p.set_defaults(func=cmd_import)
    p = sub.add_parser('export'); p.add_argument('--format', default='csv', choices=['csv','json','sqlite','all']); p.add_argument('--filename'); p.add_argument('--output'); p.add_argument('--limit', type=int, default=100000); p.set_defaults(func=cmd_export)
    sub.add_parser('stats').set_defaults(func=cmd_stats)
    p = sub.add_parser('quality'); p.add_argument('--output'); p.set_defaults(func=cmd_quality)
    p = sub.add_parser('backup'); p.add_argument('action', choices=['create','list','restore','rotate']); p.add_argument('--label', default=''); p.add_argument('--path', default=''); p.set_defaults(func=cmd_backup)
    p = sub.add_parser('merge'); p.add_argument('--directory'); p.add_argument('--files', nargs='+'); p.add_argument('--output'); p.add_argument('--strategy', default='highest_confidence', choices=['highest_confidence','longest_translation','most_sources']); p.set_defaults(func=cmd_merge)
    p = sub.add_parser('plugins'); p.add_argument('action', choices=['list','create']); p.add_argument('--name', default='my_plugin'); p.set_defaults(func=cmd_plugins)
    args = parser.parse_args()
    if not args.command: parser.print_help(); return
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    try: args.func(args)
    except Exception as e: logging.error(f"Error: {e}"); sys.exit(1)

if __name__ == '__main__': main()