"""In-memory view of the store used for keyword search + candidate lookups. Rebuilt when ingestion changes."""
import re

from ..text_utils import STOPWORDS, tokenize
from .bm25 import BM25Index

COMMON_WORDS = STOPWORDS | {
    "will", "mark", "rose", "may", "june", "april", "august", "grant", "king", "hall", "young", "long", "best",
    "good", "work", "page", "bill", "jack", "frank", "sue", "art", "ray", "dean", "hope", "faith", "joy", "love",
}


class RetrievalIndex:
    def __init__(self, ids, docs, metas, candidates: list[dict], cfg_synonyms=None):
        self.ids, self.docs, self.metas = ids, docs, metas
        self.pos = {i: n for n, i in enumerate(ids)}
        # BM25 text also includes the section so "skills" / "education" queries hit the right chunks
        self.bm25 = BM25Index([f"{m.get('section', '')} {d}" for d, m in zip(docs, metas)])
        self.by_candidate: dict[str, list[int]] = {}
        for n, m in enumerate(metas):
            self.by_candidate.setdefault(m["candidate_id"], []).append(n)
        for lst in self.by_candidate.values():
            lst.sort(key=lambda n: self.metas[n].get("chunk_index", 0))
        self.candidates = {c["candidate_id"]: c for c in candidates}
        self._name_tokens = {}
        for cid, c in self.candidates.items():
            toks = [t for t in re.findall(r"[a-z][a-z'’\-]+", c.get("name", "").lower()) if len(t) >= 3]
            self._name_tokens[cid] = toks

    @property
    def size(self):
        return len(self.ids)

    def header_chunk(self, cid):
        for n in self.by_candidate.get(cid, []):
            if self.metas[n].get("section") == "HEADER":
                return n
        return None

    def detect_candidates(self, text: str) -> list[str]:
        """Which candidates does the text talk about by name? Best (most name-tokens matched) wins."""
        low = text.lower()
        qtoks = set(re.findall(r"[a-z][a-z'’\-]+", low))
        scored = {}
        for cid, c in self.candidates.items():
            full = c.get("name", "").lower().strip()
            if full and full in low:
                scored[cid] = 100 + len(full)
                continue
            toks = self._name_tokens[cid]
            hits = [t for t in toks if t in qtoks and t not in COMMON_WORDS]
            if hits:
                scored[cid] = len(hits)
        if not scored:
            return []
        best = max(scored.values())
        return [cid for cid, s in scored.items() if s == best]
