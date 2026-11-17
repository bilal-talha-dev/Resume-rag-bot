"""Stage 1 — LOAD: file -> plain text. Add formats by registering a new loader."""
import os
import re

from ..registry import register, available, get
from ..types import LoaderError

BULLET_CHARS = "•▪◦●■‣∙·"


def normalize_text(raw: str) -> str:
    text = raw.replace("(cid:127)", "•").replace("\x7f", "•").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    lines = []
    for ln in text.split("\n"):
        ln = ln.strip()
        if ln and ln[0] in BULLET_CHARS:
            ln = "• " + ln[1:].strip()
        if ln:
            lines.append(ln)
    return "\n".join(lines)


class BaseLoader:
    extensions: tuple = ()

    def load(self, path: str) -> str:
        raise NotImplementedError


@register("loader", "pdf")
class PdfLoader(BaseLoader):
    extensions = (".pdf",)

    def load(self, path):
        pages, errors = [], []
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                pages = [p.extract_text() or "" for p in pdf.pages]
        except ImportError:
            pass
        except Exception as e:
            errors.append(f"pdfplumber: {e}")
        if not "".join(pages).strip():
            try:
                import pypdf
                pages = [p.extract_text() or "" for p in pypdf.PdfReader(path).pages]
            except Exception as e:
                errors.append(f"pypdf: {e}")
        text = normalize_text("\n".join(pages))
        if not text:
            hint = "; ".join(errors) or "scanned/image-only PDF? it needs OCR"
            raise LoaderError(f"no extractable text ({hint})")
        return text


@register("loader", "docx")
class DocxLoader(BaseLoader):
    extensions = (".docx",)

    def load(self, path):
        try:
            import docx
        except ImportError as e:
            raise LoaderError("python-docx not installed: pip install python-docx") from e
        d = docx.Document(path)
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        parts = []
        for child in d.element.body.iterchildren():
            if child.tag.endswith("}p"):
                parts.append(Paragraph(child, d).text)
            elif child.tag.endswith("}tbl"):
                for row in Table(child, d).rows:
                    cells = []
                    for c in row.cells:
                        t = c.text.strip()
                        if t and t not in cells:
                            cells.append(t)
                    parts.append(" | ".join(cells))
        text = normalize_text("\n".join(parts))
        if not text:
            raise LoaderError("document is empty")
        return text


@register("loader", "text")
class TextLoader(BaseLoader):
    extensions = (".txt", ".md", ".text")

    def load(self, path):
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    text = normalize_text(f.read())
                break
            except UnicodeDecodeError:
                continue
        else:
            raise LoaderError("cannot decode text file")
        if not text:
            raise LoaderError("file is empty")
        return text


def load_file(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    for name in available("loader"):
        cls = get("loader", name)
        if ext in cls.extensions:
            return cls().load(path)
    raise LoaderError(f"no loader registered for '{ext}' files")
