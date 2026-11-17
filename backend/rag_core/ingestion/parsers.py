"""Stage 2 — PARSE: text -> ParsedResume (candidate identity + ordered sections). Generic, layout-tolerant."""
import os
import re

from ..registry import register
from ..types import ParsedResume

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
LINK_RE = re.compile(r"(?:https?://)?(?:www\.)?(?:linkedin\.com|github\.com|gitlab\.com|behance\.net)/[^\s|,;]+", re.I)
NAME_LINE_RE = re.compile(r"^[A-Za-z][A-Za-z'’.\-]+(?:\s+[A-Za-z][A-Za-z'’.\-]+){1,3}$")
NOT_NAME_WORDS = {
    "developer", "engineer", "manager", "analyst", "designer", "consultant", "architect", "scientist",
    "specialist", "intern", "lead", "director", "officer", "administrator", "stack", "senior", "junior",
    "software", "data", "resume", "curriculum", "vitae", "cv", "profile", "summary", "experience",
    "education", "skills", "projects", "full", "front", "back", "end", "web", "mobile", "cloud",
    "devops", "machine", "learning", "product", "project", "marketing", "sales", "technical",
}
FILENAME_NOISE = {"resume", "cv", "full", "final", "updated", "copy", "new", "latest", "curriculum", "vitae", "docx", "pdf"}


def _norm_header(s: str) -> str:
    s = s.lower().replace(" and ", " & ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z& ]", " ", s)).strip()


def name_from_filename(path: str) -> str:
    stem = os.path.splitext(os.path.basename(path))[0]
    toks = [t for t in re.split(r"[_\-.\s]+", stem) if t and not t.isdigit() and not re.fullmatch(r"v\d+", t.lower())]
    toks = [t for t in toks if t.lower() not in FILENAME_NOISE]
    return " ".join(t.capitalize() if t.islower() or t.isupper() else t for t in toks) or stem


@register("parser", "resume")
class ResumeParser:
    def __init__(self, config):
        icfg = config.section("ingestion")
        self.name_source = icfg.get("candidate_name_source", "auto")
        self.detect_unknown = bool(icfg.get("detect_unknown_headers", False))
        self.alias_map = {}
        for canon, aliases in icfg.get("section_aliases", {}).items():
            self.alias_map[_norm_header(canon)] = canon.upper()
            for a in aliases:
                self.alias_map[_norm_header(a)] = canon.upper()

    # -- helpers ---------------------------------------------------------------
    def _is_bullet(self, line):
        return line.startswith("•")

    def _header_of(self, line):
        if self._is_bullet(line) or len(line) > 50:
            return None
        return self.alias_map.get(_norm_header(line))

    def _looks_like_unknown_header(self, line):
        return (self.detect_unknown and line.isupper() and 3 <= len(line) <= 30
                and re.fullmatch(r"[A-Z &/]+", line) and len(line.split()) <= 4)

    def _find_name(self, lines):
        for ln in lines[:6]:
            if self._header_of(ln) or EMAIL_RE.search(ln) or any(c.isdigit() for c in ln) or "@" in ln:
                continue
            if not NAME_LINE_RE.match(ln) or len(ln) > 40:
                continue
            words = re.split(r"[\s.]+", ln.lower())
            if any(w in NOT_NAME_WORDS for w in words):
                continue
            return ln.title() if ln.isupper() else ln
        return None

    # -- main ------------------------------------------------------------------
    def parse(self, text: str, source: str) -> ParsedResume:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        text_name = self._find_name(lines)
        file_name = name_from_filename(source)
        name = {"text": text_name or file_name, "filename": file_name}.get(self.name_source, text_name or file_name)

        sections, cur_title, cur = [], "HEADER", []
        for i, ln in enumerate(lines):
            canon = self._header_of(ln)
            if canon is None and i > 0 and self._looks_like_unknown_header(ln):
                canon = ln.upper()
            if canon:
                if cur:
                    sections.append((cur_title, cur))
                cur_title, cur = canon, []
            else:
                cur.append(ln)
        if cur:
            sections.append((cur_title, cur))

        header_text = "\n".join(sections[0][1]) if sections and sections[0][0] == "HEADER" else "\n".join(lines[:8])
        email = (EMAIL_RE.search(header_text) or EMAIL_RE.search(text))
        phone = PHONE_RE.search(header_text)
        links = list(dict.fromkeys(m.group(0) for m in LINK_RE.finditer(text)))[:4]
        headline = ""
        if sections and sections[0][0] == "HEADER":
            for ln in sections[0][1][:4]:
                if ln != name and not EMAIL_RE.search(ln) and not PHONE_RE.search(ln) and len(ln) <= 80 and "http" not in ln.lower():
                    headline = ln
                    break
        return ParsedResume(source=source, name=name, email=email.group(0) if email else "",
                            phone=phone.group(0).strip() if phone else "", links=links,
                            headline=headline, sections=sections, raw_text=text)
