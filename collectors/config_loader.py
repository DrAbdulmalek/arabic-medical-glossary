"""
تحميل إعدادات config.yaml للمشروع.
"""

import yaml
from pathlib import Path


def load_config() -> dict:
    """تحميل إعدادات المشروع من config.yaml"""
    config_path = Path("config.yaml")
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    return {}