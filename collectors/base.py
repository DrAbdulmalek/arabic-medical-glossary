"""
Base collector with retry, deduplication, and robust error handling.
"""

import json
import os
import time
import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collectors.config_loader import load_config as _load_config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TermEntry:
    """بنية موحدة لكل مصطلح"""
    term: str
    definition: str
    source: str
    language: str
    confidence: float = 1.0
    tags: List[str] = None
    raw_text: str = ""
    date_added: str = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.date_added is None:
            self.date_added = datetime.now().isoformat()

    def get_hash(self) -> str:
        """مفتاح فريد يعتمد على المصطلح والمصدر"""
        content = f"{self.term.lower().strip()}:{self.source}:{self.language}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class BaseCollector(ABC):
    """فئة أساسية مُحسّنة لجميع المجمعات"""

    def __init__(self, source_name: str, source_url: str, config: dict = None):
        self.source_name = source_name
        self.source_url = source_url
        self.config = config or _load_config()

        self.data_dir = os.path.join("data", "sources")
        self.progress_dir = os.path.join("data", "progress")
        self.log_dir = os.path.join("data", "logs")

        for d in [self.data_dir, self.progress_dir, self.log_dir]:
            os.makedirs(d, exist_ok=True)

        self.source_file = os.path.join(
            self.data_dir, 
            f"{source_name.lower().replace(' ', '_')}.json"
        )
        self.progress_file = os.path.join(self.progress_dir, "state.json")
        self.log_file = os.path.join(
            self.log_dir, 
            f"{source_name}_{datetime.now().strftime('%Y%m%d')}.log"
        )

        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.session.mount('http://', HTTPAdapter(max_retries=retries))

        self.logger = self._setup_logger()

        # Batch buffer لتقليل عمليات I/O
        self._data_cache = None
        self._dirty = False
        self._buffer_size = self.config.get("collection", {}).get("buffer_size", 500)
        self._pending_count = 0

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(self.source_name)
        handler = logging.FileHandler(self.log_file, encoding='utf-8')
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def load_progress(self) -> dict:
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                "sources": {},
                "total_terms": 0,
                "last_update": None,
                "errors_log": []
            }

    def save_progress(self, progress: dict):
        progress["last_update"] = datetime.now().isoformat()
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)

    def load_source_data(self) -> dict:
        # استخدام الذاكرة المؤقتة إن وجدت
        if self._data_cache is not None:
            return self._data_cache
        try:
            with open(self.source_file, 'r', encoding='utf-8') as f:
                self._data_cache = json.load(f)
                return self._data_cache
        except FileNotFoundError:
            self._data_cache = {
                "terms": {},
                "metadata": {
                    "source": self.source_name,
                    "created": datetime.now().isoformat()
                }
            }
            return self._data_cache

    def save_source_data(self, data: dict):
        data["metadata"]["last_updated"] = datetime.now().isoformat()
        with open(self.source_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self._data_cache = data
        self._dirty = False
        self._pending_count = 0

    def add_term(self, entry: TermEntry) -> bool:
        data = self.load_source_data()
        term_hash = entry.get_hash()

        if term_hash in data["terms"]:
            existing = data["terms"][term_hash]
            if entry.confidence > existing.get("confidence", 0):
                data["terms"][term_hash] = asdict(entry)
                self.logger.info(f"🔄 تحديث: {entry.term}")
                self._dirty = True
                if self._pending_count >= self._buffer_size:
                    self.save_source_data(data)
                else:
                    self._pending_count += 1
                return True
            return False

        data["terms"][term_hash] = asdict(entry)
        self._dirty = True
        self._pending_count += 1

        # حفظ دفعي عند الوصول للحد
        if self._pending_count >= self._buffer_size:
            self.save_source_data(data)
            self.logger.info(f"💾 حفظ دفعة: {self._pending_count} مصطلح (إجمالي: {len(data['terms'])})")
        else:
            self.logger.info(f"✅ جديد: {entry.term}")

        return True

    def flush(self):
        """حفظ أي مصطلحات متبقية في الذاكرة"""
        if self._dirty and self._data_cache is not None:
            self.save_source_data(self._data_cache)
            self.logger.info("💾 تم حفظ المصطلحات المتبقية")

    def get_stats(self) -> dict:
        data = self.load_source_data()
        return {
            "source": self.source_name,
            "total_terms": len(data["terms"]),
            "file_size_mb": round(
                os.path.getsize(self.source_file) / (1024*1024), 2
            ) if os.path.exists(self.source_file) else 0,
            "last_updated": data.get("metadata", {}).get("last_updated", "غير معروف")
        }

    def rate_limit(self, delay: float = 1.0):
        time.sleep(delay)

    @abstractmethod
    def collect(self) -> int:
        pass

    def run(self) -> dict:
        self.logger.info(f"🚀 بدء الجمع من: {self.source_name}")

        progress = self.load_progress()
        if self.source_name not in progress["sources"]:
            progress["sources"][self.source_name] = {
                "status": "idle",
                "last_run": None,
                "terms_collected": 0,
                "last_error": None,
                "consecutive_failures": 0
            }

        source_progress = progress["sources"][self.source_name]
        source_progress["status"] = "running"
        source_progress["last_run"] = datetime.now().isoformat()
        self.save_progress(progress)

        try:
            new_count = self.collect()
            # حفظ أي مصطلحات متبقية في الـ buffer
            self.flush()

            source_progress["status"] = "completed"
            source_progress["terms_collected"] = len(
                self.load_source_data()["terms"]
            )
            source_progress["consecutive_failures"] = 0
            source_progress["last_error"] = None

            self.logger.info(f"✅ اكتمل: {new_count} مصطلح جديد")

        except Exception as e:
            source_progress["status"] = "failed"
            source_progress["last_error"] = str(e)
            source_progress["consecutive_failures"] += 1
            progress["errors_log"].append({
                "source": self.source_name,
                "error": str(e),
                "time": datetime.now().isoformat()
            })
            self.logger.error(f"❌ فشل: {e}")
            new_count = 0

        total = sum(
            s.get("terms_collected", 0) 
            for s in progress["sources"].values()
        )
        progress["total_terms"] = total
        self.save_progress(progress)

        return {
            "source": self.source_name,
            "new_terms": new_count if source_progress["status"] == "completed" else 0,
            "status": source_progress["status"],
            "total_in_source": source_progress["terms_collected"]
        }
