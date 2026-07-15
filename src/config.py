"""Configuration constants for the Arabic Medical Glossary project."""

import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = PROJECT_ROOT / "data"
DB_PATH: Path = PROJECT_ROOT / "glossary.db"
BACKUP_DIR: Path = PROJECT_ROOT / "backups"
PLUGINS_DIR: Path = PROJECT_ROOT / "plugins"
INGESTION_DIR: Path = PROJECT_ROOT / "ingestion"

# Ensure directories exist
for _d in (BACKUP_DIR, PLUGINS_DIR, INGESTION_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Supported file extensions
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS: set = {
    ".csv", ".tsv", ".json", ".jsonl", ".txt",
    ".xlsx", ".xls", ".pdf", ".docx", ".doc",
    ".epub", ".html", ".htm", ".xml", ".tmx",
}

# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------
CONFIDENCE_LEVELS: dict = {
    "very_high": 0.95,
    "high": 1.0,
    "medium": 0.7,
    "low": 0.5,
    "unknown": 0.3,
}

# ---------------------------------------------------------------------------
# Term types
# ---------------------------------------------------------------------------
TERM_TYPES: list = [
    "term",
    "abbreviation",
    "phrase",
    "sentence",
    "drug_name",
    "brand_name",
    "generic_name",
    "medical_device",
    "anatomy",
    "procedure",
    "diagnosis",
    "symptom",
    "lab_test",
    "unit",
]

# ---------------------------------------------------------------------------
# Validation statuses
# ---------------------------------------------------------------------------
VALIDATION_STATUSES: list = [
    "unverified",
    "verified",
    "pending_review",
    "rejected",
    "needs_expert",
]

# ---------------------------------------------------------------------------
# Term complexities
# ---------------------------------------------------------------------------
TERM_COMPLEXITIES: list = [
    "simple",
    "moderate",
    "complex",
    "highly_technical",
]

# ---------------------------------------------------------------------------
# Medical specialties (30 items)
# ---------------------------------------------------------------------------
MEDICAL_SPECIALTIES: list = [
    "Cardiology",
    "Neurology",
    "Oncology",
    "Pediatrics",
    "Surgery",
    "Orthopedics",
    "Dermatology",
    "Ophthalmology",
    "ENT",
    "Gastroenterology",
    "Pulmonology",
    "Endocrinology",
    "Nephrology",
    "Urology",
    "Gynecology",
    "Obstetrics",
    "Psychiatry",
    "Radiology",
    "Pathology",
    "Anesthesiology",
    "Emergency Medicine",
    "Internal Medicine",
    "Rheumatology",
    "Hematology",
    "Infectious Disease",
    "Toxicology",
    "Pharmacology",
    "Immunology",
    "Genetics",
    "Dentistry",
]

# ---------------------------------------------------------------------------
# Regions
# ---------------------------------------------------------------------------
REGIONS: list = [
    "global",
    "mena",
    "gulf",
    "levant",
    "north_africa",
    "egypt",
    "saudi_arabia",
    "uae",
    "jordan",
    "lebanon",
    "iraq",
    "morocco",
    "tunisia",
    "algeria",
    "sudan",
]

# ---------------------------------------------------------------------------
# Quality thresholds
# ---------------------------------------------------------------------------
MIN_CONFIDENCE_THRESHOLD: float = 0.5
HIGH_CONFIDENCE_THRESHOLD: float = 0.8
MAX_ENGLISH_LENGTH: int = 500
MAX_ARABIC_LENGTH: int = 500
MIN_TERM_LENGTH: int = 1
MAX_DUPLICATE_RATIO: float = 0.95
MAX_LATIN_IN_ARABIC_RATIO: float = 0.3

# ---------------------------------------------------------------------------
# API / external service config
# ---------------------------------------------------------------------------
API_CONFIG: dict = {
    "huggingface": {
        "repo_name": "arabic-medical-glossary",
        "organization": None,
        "private": False,
    },
    "batch_size": 10000,
    "max_workers": 4,
    "request_timeout": 30,
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: int = logging.INFO
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"