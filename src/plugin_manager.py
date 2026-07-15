import importlib.util, logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class PluginInterface:
    @staticmethod
    def name() -> str: raise NotImplementedError
    @staticmethod
    def description() -> str: raise NotImplementedError
    @staticmethod
    def supported_extensions() -> List[str]: raise NotImplementedError
    @staticmethod
    def extract(file_path: str) -> List[Dict]: raise NotImplementedError
    @staticmethod
    def validate(data: List[Dict]) -> List[Dict]: return []

class PluginManager:
    def __init__(self, plugins_dir='plugins'):
        self.plugins_dir = Path(plugins_dir); self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.plugins: Dict[str, Any] = {}; self._builtin: Dict[str, Any] = {}

    def register_builtin(self, name, plugin_class):
        self._builtin[name] = plugin_class; logger.info(f"Registered builtin: {name}")

    def load_plugins(self):
        results = {}
        for f in self.plugins_dir.glob('*.py'):
            if f.name.startswith('_'): continue
            try:
                spec = importlib.util.spec_from_file_location(f.stem, str(f))
                mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if isinstance(attr, type) and issubclass(attr, PluginInterface) and attr is not PluginInterface:
                        self.plugins[attr.name()] = attr; results[attr.name()] = 1
                        logger.info(f"Loaded plugin: {attr.name()}")
            except Exception as e:
                results[f.stem] = 0; logger.error(f"Failed to load {f.stem}: {e}")
        return results

    def get_plugin(self, name):
        return self._builtin.get(name) or self.plugins.get(name)

    def list_plugins(self):
        result = []
        for n, p in {**self._builtin, **self.plugins}.items():
            result.append({'name': n, 'description': getattr(p, 'description', lambda: '')(), 'extensions': getattr(p, 'supported_extensions', lambda: [])(), 'source': 'builtin' if n in self._builtin else 'loaded'})
        return result

    def extract_with_plugin(self, plugin_name, file_path):
        p = self.get_plugin(plugin_name)
        if p: return p.extract(file_path)
        logger.error(f"Plugin not found: {plugin_name}"); return []

    def auto_detect_plugin(self, file_path):
        ext = Path(file_path).suffix.lower()
        for n, p in {**self._builtin, **self.plugins}.items():
            if ext in getattr(p, 'supported_extensions', lambda: [])(): return n
        return None

    def extract_auto(self, file_path):
        name = self.auto_detect_plugin(file_path)
        if name: return self.extract_with_plugin(name, file_path)
        logger.warning(f"No plugin for: {file_path}"); return []

    def create_plugin_template(self, name):
        cls = ''.join(w.capitalize() for w in name.split('_')) + 'Plugin'
        content = f'''"""Plugin: {name}"""
from src.plugin_manager import PluginInterface
from typing import List, Dict

class {cls}(PluginInterface):
    @staticmethod
    def name() -> str: return "{name}"
    @staticmethod
    def description() -> str: return "Describe this plugin."
    @staticmethod
    def supported_extensions() -> List[str]: return [".ext"]
    @staticmethod
    def extract(file_path: str) -> List[Dict]:
        terms = []
        # Your extraction logic here
        return terms
'''
        path = self.plugins_dir / f"{name}_plugin.py"
        path.write_text(content, encoding='utf-8'); logger.info(f"Template created: {path}"); return str(path)

class BuiltinCSVPlugin(PluginInterface):
    @staticmethod
    def name(): return "csv"
    @staticmethod
    def description(): return "CSV/TSV glossary files"
    @staticmethod
    def supported_extensions(): return [".csv", ".tsv"]
    @staticmethod
    def extract(file_path):
        import csv
        results = []
        for enc in ['utf-8-sig', 'utf-8', 'latin-1']:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        en = row.get('en', row.get('english', row.get('term_en', '')))
                        ar = row.get('ar', row.get('arabic', row.get('term_ar', '')))
                        if en and ar: results.append({'english': en.strip(), 'arabic': ar.strip(), 'source': row.get('source', Path(file_path).stem)})
                break
            except: continue
        return results

class BuiltinJSONPlugin(PluginInterface):
    @staticmethod
    def name(): return "json"
    @staticmethod
    def description(): return "JSON glossary files"
    @staticmethod
    def supported_extensions(): return [".json"]
    @staticmethod
    def extract(file_path):
        import json
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict): data = data.get('terms', data.get('data', [data]))
        return data if isinstance(data, list) else [data]