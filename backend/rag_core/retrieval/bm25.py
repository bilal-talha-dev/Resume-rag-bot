import math
from collections import Counter

from ..text_utils import tokenize


class BM25Index:
    """Inverted-index BM25 built once per ingest revision; scoring touches only matching postings."""

    def __init__(self, texts: list[str], k1: float = 1.4, b: float = 0.75):
        self.k1, self.b = k1, b
        docs = [tokenize(t) for t in texts]
        self.n = len(docs)
        self.lens = [len(d) for d in docs]
        self.avg = (sum(self.lens) / self.n) if self.n else 1.0
        self.postings: dict[str, dict[int, int]] = {}
        for i, d in enumerate(docs):
            for term, tf in Counter(d).items():
                self.postings.setdefault(term, {})[i] = tf

    def scores(self, query_terms: list[str], allowed: set = None) -> dict[int, float]:
        out: dict[int, float] = {}
        for term in set(query_terms):
            post = self.postings.get(term)
            if not post:
                continue
            idf = math.log(1 + (self.n - len(post) + 0.5) / (len(post) + 0.5))
            for i, tf in post.items():
                if allowed is not None and i not in allowed:
                    continue
                norm = tf + self.k1 * (1 - self.b + self.b * self.lens[i] / self.avg)
                out[i] = out.get(i, 0.0) + idf * tf * (self.k1 + 1) / norm
        return out
