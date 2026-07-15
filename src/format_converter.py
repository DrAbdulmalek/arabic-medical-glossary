import subprocess, logging, os, re
from pathlib import Path
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class FormatConverter:
    SUPPORTED = ['.pdf', '.docx', '.doc', '.epub', '.html', '.htm', '.rtf', '.odt', '.txt', '.md']

    def __init__(self, output_dir='.converted'):
        self.output_dir = Path(output_dir); self.output_dir.mkdir(parents=True, exist_ok=True)

    def convert(self, input_path, output_path=None):
        p = Path(input_path); ext = p.suffix.lower()
        out = Path(output_path) if output_path else self.output_dir / (p.stem + '.txt')
        if ext == '.pdf': return self._pdf(p, out)
        elif ext in ('.docx',): return self._docx(p, out)
        elif ext == '.doc': return self._doc(p, out)
        elif ext == '.epub': return self._epub(p, out)
        elif ext in ('.html', '.htm'): return self._html(p, out)
        elif ext in ('.rtf', '.odt'): return self._libre(p, out)
        elif ext in ('.txt', '.md'): return self._copy(p, out)
        else: raise ValueError(f"Unsupported: {ext}")

    def _pdf(self, p, out):
        try:
            r = subprocess.run(['pdftotext', str(p), str(out)], capture_output=True, text=True, timeout=60)
            if r.returncode == 0: return str(out)
        except: pass
        try:
            import fitz; doc = fitz.open(str(p)); text = '\n'.join(page.get_text() for page in doc); doc.close()
            out.write_text(text, encoding='utf-8'); return str(out)
        except ImportError: pass
        except: pass
        try:
            import pdfplumber
            with pdfplumber.open(str(p)) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            out.write_text(text, encoding='utf-8'); return str(out)
        except ImportError: logger.warning("Install pdfplumber or PyMuPDF for PDF conversion")
        raise RuntimeError("No PDF backend available")

    def _docx(self, p, out):
        try:
            from docx import Document; doc = Document(str(p))
            text = '\n'.join(p.text for p in doc.paragraphs); out.write_text(text, encoding='utf-8'); return str(out)
        except ImportError: return self._libre(p, out)

    def _doc(self, p, out):
        try:
            r = subprocess.run(['antiword', str(p)], capture_output=True, text=True, timeout=30)
            if r.returncode == 0: out.write_text(r.stdout, encoding='utf-8'); return str(out)
        except: pass
        return self._libre(p, out)

    def _epub(self, p, out):
        try:
            r = subprocess.run(['ebook-convert', str(p), str(out)], capture_output=True, text=True, timeout=120)
            if r.returncode == 0: return str(out)
        except: pass
        import zipfile, re
        try:
            with zipfile.ZipFile(str(p)) as zf:
                texts = []
                for name in zf.namelist():
                    if name.endswith(('.html', '.htm', '.xhtml')):
                        html = zf.read(name).decode('utf-8', errors='ignore')
                        texts.append(re.sub(r'<[^>]+>', ' ', html))
                out.write_text('\n'.join(texts), encoding='utf-8'); return str(out)
        except Exception as e: raise RuntimeError(f"EPUB conversion failed: {e}")

    def _html(self, p, out):
        try:
            import html2text; text = html2text.html2text(p.read_text(encoding='utf-8')); out.write_text(text, encoding='utf-8'); return str(out)
        except ImportError: pass
        try:
            from bs4 import BeautifulSoup; soup = BeautifulSoup(p.read_text(encoding='utf-8'), 'html.parser')
            out.write_text(soup.get_text(separator='\n'), encoding='utf-8'); return str(out)
        except ImportError:
            text = re.sub(r'<[^>]+>', ' ', p.read_text(encoding='utf-8', errors='ignore')); out.write_text(text, encoding='utf-8'); return str(out)

    def _libre(self, p, out):
        r = subprocess.run(['libreoffice', '--headless', '--convert-to', 'txt:Text', '--outdir', str(self.output_dir), str(p)], capture_output=True, text=True, timeout=120)
        txt = self.output_dir / (p.stem + '.txt')
        if txt.exists(): return str(txt)
        raise RuntimeError("LibreOffice conversion failed")

    def _copy(self, p, out):
        import shutil; shutil.copy2(str(p), str(out)); return str(out)

    def batch_convert(self, input_dir, output_dir=None, recursive=True):
        od = Path(output_dir) if output_dir else self.output_dir; results = {}
        pattern = '**/*' if recursive else '*'
        for f in Path(input_dir).glob(pattern):
            if f.is_file() and f.suffix.lower() in self.SUPPORTED:
                try: results[str(f)] = self.convert(str(f), str(od / (f.stem + '.txt')))
                except Exception as e: results[str(f)] = f"Error: {e}"
        return results

    def is_supported(self, file_path): return Path(file_path).suffix.lower() in self.SUPPORTED