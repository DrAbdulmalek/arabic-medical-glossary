"""
Parse glossary entries from raw text using multiple strategies.
Supports Arabic and English medical terms.
"""

import re
from typing import List
from dataclasses import dataclass

from collectors.base import TermEntry


def parse_glossary_from_text(text: str, source: str = "unknown") -> List[TermEntry]:
    """
    تحليل النص واستخراج مصطلحات وتعريفات
    """
    if not text or len(text) < 10:
        return []

    entries = []
    entries.extend(_pattern_colon(text, source))
    entries.extend(_pattern_numbered(text, source))
    entries.extend(_pattern_table(text, source))
    entries.extend(_pattern_parentheses(text, source))

    seen = set()
    filtered = []
    for entry in entries:
        key = f"{entry.term.lower().strip()}:{entry.definition[:50]}"
        if key not in seen and len(entry.term) > 1 and len(entry.definition) > 5:
            seen.add(key)
            filtered.append(entry)

    return filtered


def _pattern_colon(text: str, source: str) -> List[TermEntry]:
    entries = []
    pattern = r'([^\n:]{2,80})[:：]\s*([^\n]{5,500})'
    matches = re.findall(pattern, text)

    for term, definition in matches:
        term = term.strip()
        definition = definition.strip()

        if re.match(r'^(الفصل|Chapter|Section|القسم)', term):
            continue

        lang = _detect_language(term)
        entries.append(TermEntry(
            term=term,
            definition=definition,
            source=source,
            language=lang,
            confidence=0.8
        ))

    return entries


def _pattern_numbered(text: str, source: str) -> List[TermEntry]:
    entries = []
    pattern = r'(?:^|\n)\s*\d+[.)]\s*([^\n-]{2,80})\s*[-–]\s*([^\n]{5,500})'
    matches = re.findall(pattern, text)

    for term, definition in matches:
        lang = _detect_language(term)
        entries.append(TermEntry(
            term=term.strip(),
            definition=definition.strip(),
            source=source,
            language=lang,
            confidence=0.75
        ))

    return entries


def _pattern_table(text: str, source: str) -> List[TermEntry]:
    entries = []
    lines = text.split('\n')

    for line in lines:
        parts = re.split(r'\s*[|\t]\s*', line.strip())
        if len(parts) == 2 and len(parts[0]) > 1 and len(parts[1]) > 5:
            lang = _detect_language(parts[0])
            entries.append(TermEntry(
                term=parts[0].strip(),
                definition=parts[1].strip(),
                source=source,
                language=lang,
                confidence=0.7
            ))

    return entries


def _pattern_parentheses(text: str, source: str) -> List[TermEntry]:
    entries = []
    pattern = r'([^\n(]{2,50})\s*\(\s*([^\)]{5,200})\s*\)'
    matches = re.findall(pattern, text)

    for term, definition in matches:
        if len(definition) < 20:
            continue

        lang = _detect_language(term)
        entries.append(TermEntry(
            term=term.strip(),
            definition=definition.strip(),
            source=source,
            language=lang,
            confidence=0.6
        ))

    return entries


def _detect_language(text: str) -> str:
    arabic_chars = len(re.findall(r'[\u0600-\u06FF]', text))
    total_chars = len(re.findall(r'[a-zA-Z\u0600-\u06FF]', text))

    if total_chars == 0:
        return "unknown"

    ratio = arabic_chars / total_chars
    return "ar" if ratio > 0.3 else "en"
