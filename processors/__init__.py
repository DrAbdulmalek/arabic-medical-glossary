"""
Text processing and glossary extraction modules.
"""

from .text_extractor import extract_text_from_file
from .glossary_parser import parse_glossary_from_text
from .merge_sources import merge_all_sources

__all__ = [
    "extract_text_from_file",
    "parse_glossary_from_text",
    "merge_all_sources"
]
