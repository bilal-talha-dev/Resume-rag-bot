"""Stage 3 — CHUNK: ParsedResume -> list[Chunk]. Every chunk text starts with [Candidate | SECTION | entry]."""
import re

from ..registry import register
from ..types import Chunk, ParsedResume

_MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
DATE_RANGE_RE = re.compile(
    rf"(?:{_MONTH}\s+)?(?:19|20)\d{{2}}\s*(?:-|–|—|to)\s*(?:{_MONTH}\s+)?(?:(?:19|20)\d{{2}}|present|current|now|ongoing)",
    re.I)


def split_by_size(lines: list[str], max_chars: int, overlap: int) -> list[list[str]]:
    groups, cur, size = [], [], 0
    for ln in lines:
        if cur and size + len(ln) + 1 > max_chars:
            groups.append(cur)
            keep, tot = [], 0
            for prev in reversed(cur):          # carry a tail of the previous chunk as overlap
                if tot + len(prev) > overlap:
                    break
                keep.insert(0, prev)
                tot += len(prev)
            cur, size = keep, tot
        cur.append(ln)
        size += len(ln) + 1
    if cur:
        groups.append(cur)
    return groups


def split_entries(lines: list[str]) -> list[tuple[str, list[str]]]:
    """Split an EXPERIENCE/PROJECTS section into one entry per role/project."""
    def is_header(ln):
        return (not ln.startswith("•") and len(ln) <= 160 and ("|" in ln or DATE_RANGE_RE.search(ln)))
    entries, title, cur = [], "", []
    for ln in lines:
        if is_header(ln):
            if cur:
                entries.append((title, cur))
            title, cur = ln[:100], [ln]
        else:
            cur.append(ln)
    if cur:
        entries.append((title, cur))
    return entries


class BaseChunker:
    def __init__(self, config):
        c = config.get("ingestion.chunk", {})
        self.max_chars = int(c.get("max_chars", 1200))
        self.overlap = int(c.get("overlap_chars", 150))
        self.min_chars = int(c.get("min_chars", 80))
        self.split_sections = {s.upper() for s in c.get("split_entries", [])}

    def chunk(self, parsed: ParsedResume, candidate_id: str) -> list[Chunk]:
        raise NotImplementedError


def _make(parsed, candidate_id, section, entry, lines, idx):
    label = f"{parsed.name} | {section}" + (f" | {entry}" if entry else "")
    return Chunk(id=f"{candidate_id}:{idx:03d}", candidate_id=candidate_id, candidate_name=parsed.name,
                 source=parsed.source, section=section, entry=entry, index=idx,
                 text=f"[{label}] " + "\n".join(lines))


@register("chunker", "section")
class SectionChunker(BaseChunker):
    """One chunk per section; EXPERIENCE/PROJECTS split per role/project; oversize pieces are windowed."""

    def chunk(self, parsed, candidate_id):
        chunks, idx = [], 0
        for section, lines in parsed.sections:
            units = split_entries(lines) if section in self.split_sections else [("", lines)]
            for entry, ulines in units:
                for piece in split_by_size(ulines, self.max_chars, self.overlap):
                    body = "\n".join(piece)
                    if (chunks and len(body) < self.min_chars and chunks[-1].section == section
                            and section != "HEADER"):
                        chunks[-1].text += "\n" + body          # glue tiny fragments to their neighbour
                        continue
                    chunks.append(_make(parsed, candidate_id, section, entry, piece, idx))
                    idx += 1
        return chunks


@register("chunker", "fixed")
class FixedChunker(BaseChunker):
    """Ignores structure: sliding window over the whole document."""

    def chunk(self, parsed, candidate_id):
        lines = [l for l in parsed.raw_text.split("\n") if l.strip()]
        return [_make(parsed, candidate_id, "TEXT", "", piece, i)
                for i, piece in enumerate(split_by_size(lines, self.max_chars, self.overlap))]
