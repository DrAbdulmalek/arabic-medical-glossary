"""
Extract text from various file formats with fallback strategies.
"""

import os
import re
from typing import Optional


def extract_text_from_file(file_path: str) -> Optional[str]:
    """
    استخراج النص من ملف بأي صيغة مدعومة
    """
    ext = os.path.splitext(file_path)[1].lower()

    extractors = {
        '.txt': _extract_txt,
        '.pdf': _extract_pdf,
        '.docx': _extract_docx,
        '.doc': _extract_docx,
        '.rtf': _extract_rtf,
        '.html': _extract_html,
        '.htm': _extract_html,
    }

    extractor = extractors.get(ext)

    if extractor:
        try:
            return extractor(file_path)
        except Exception:
            return _extract_raw_text(file_path)

    return _extract_raw_text(file_path)


def _extract_txt(file_path: str) -> str:
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()


def _extract_pdf(file_path: str) -> str:
    try:
        import PyPDF2
        text = []
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text.append(page_text)
        return "\n".join(text)
    except ImportError:
        try:
            import pdfplumber
            text = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    text.append(page.extract_text() or "")
            return "\n".join(text)
        except ImportError:
            return _extract_raw_text(file_path)


def _extract_docx(file_path: str) -> str:
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    except ImportError:
        return _extract_raw_text(file_path)


def _extract_rtf(file_path: str) -> str:
    try:
        from striprtf.striprtf import rtf_to_text
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return rtf_to_text(f.read())
    except ImportError:
        return _extract_raw_text(file_path)


def _extract_html(file_path: str) -> str:
    try:
        from bs4 import BeautifulSoup
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            return soup.get_text(separator='\n')
    except ImportError:
        return _extract_raw_text(file_path)


def _extract_raw_text(file_path: str) -> Optional[str]:
    """
    استخراج النص الخام من أي ملف (fallback)
    """
    try:
        with open(file_path, 'rb') as f:
            raw = f.read()

        for encoding in ['utf-8', 'utf-16', 'cp1256', 'latin-1']:
            try:
                text = raw.decode(encoding, errors='ignore')
                text = re.sub(r'[^\w\s\u0600-\u06FF\u0750-\u077F:؛،.()-]', ' ', text)
                text = re.sub(r'\s+', ' ', text)
                return text.strip()
            except:
                continue

        return None
    except Exception:
        return None
