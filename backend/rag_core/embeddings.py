"""
Embedders. Each one exposes:  id, dims, embed_documents(texts), embed_query(text).

IMPORTANT: vectors from different embedders live in different spaces, so every embedder
gets its OWN Chroma collection (named from `embedder.id`). They are never mixed.
"""
import hashlib
import json
import math
import os
import re
import time
import urllib.error
import urllib.request

from .registry import register
from .text_utils import STOPWORDS, stem
from .types import EmbeddingUnavailable

PLACEHOLDER_KEYS = {"", "your_gemini_api_key_here"}


def resolve_api_key(explicit: str = None) -> str:
    key = (explicit or os.getenv("GEMINI_API_KEY") or "").strip()
    return "" if key in PLACEHOLDER_KEYS else key


def _l2(vec: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in vec))
    return [x / n for x in vec] if n else vec


def _http_error_detail(e: urllib.error.HTTPError) -> str:
    try:
        body = json.loads(e.read().decode("utf-8"))
        return body.get("error", {}).get("message", "")[:200] or f"HTTP {e.code}"
    except Exception:
        return f"HTTP {e.code}"


def gemini_post(model: str, action: str, payload: dict, api_key: str, timeout: int = 30) -> dict:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:{action}?key={api_key}"
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class BaseEmbedder:
    provider = "base"
    model = ""
    dims = 768

    @property
    def id(self) -> str:
        return f"{self.provider}-{self.model}-{self.dims}".strip("-")

    def available(self) -> bool:
        return True

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


# --------------------------------------------------------------------------- local
@register("embedder", "local")
class LocalHashEmbedder(BaseEmbedder):
    """Deterministic hashed bag-of-words/bigram/char-gram vectors. Offline, free, decent for keywords."""
    provider = "local"
    model = "hash"

    def __init__(self, dims: int = 768, **_):
        self.dims = dims

    def _embed(self, text: str) -> list[float]:
        dims = self.dims
        vec = [0.0] * dims
        cleaned = re.sub(r"[^a-z0-9+#.\-/]", " ", text.lower())
        raw = [t.strip(".-/") for t in cleaned.split() if len(t.strip(".-/")) > 1]
        tokens = [t for t in raw if t not in STOPWORDS]
        feats = []
        for t in tokens:
            feats.append((f"tok:{stem(t)}", 3.0 if len(t) >= 5 or any(c.isdigit() for c in t) else 1.8))
            if any(c in t for c in ".-/"):
                for sub in re.split(r"[.\-/]", t):
                    if len(sub) > 1 and sub not in STOPWORDS:
                        feats.append((f"tok:{stem(sub)}", 2.5))
        for i in range(len(tokens) - 1):
            feats.append((f"bg:{stem(tokens[i])}_{stem(tokens[i + 1])}", 2.0))
        for t in tokens:
            if len(t) >= 4:
                for j in range(len(t) - 3):
                    feats.append((f"cg:{t[j:j + 4]}", 0.5))
        for feat, w in feats:
            h = int(hashlib.md5(feat.encode("utf-8")).hexdigest(), 16)
            vec[h % dims] += (1.0 if ((h >> 16) & 1) == 0 else -1.0) * w
        return _l2(vec)

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]


# --------------------------------------------------------------------------- gemini
@register("embedder", "gemini")
class GeminiEmbedder(BaseEmbedder):
    provider = "gemini"

    def __init__(self, model: str = "gemini-embedding-001", dims: int = 768, batch_size: int = 50,
                 api_key: str = None, timeout: int = 40, **_):
        self.model = model
        self.dims = dims
        self.batch_size = max(1, min(int(batch_size), 100))
        self._api_key = api_key
        self.timeout = timeout

    def _key(self) -> str:
        return resolve_api_key(self._api_key)

    def available(self) -> bool:
        return bool(self._key())

    def _call(self, action: str, payload: dict) -> dict:
        key = self._key()
        if not key:
            raise EmbeddingUnavailable("GEMINI_API_KEY not configured")
        last = "unknown error"
        for attempt in range(4):
            try:
                return gemini_post(self.model, action, payload, key, timeout=self.timeout)
            except urllib.error.HTTPError as e:
                last = _http_error_detail(e)
                if e.code in (429, 500, 502, 503) and attempt < 3:
                    time.sleep(1.5 * (2 ** attempt))      # 1.5s, 3s, 6s
                    continue
                raise EmbeddingUnavailable(f"{self.model}: {last}") from e
            except Exception as e:
                last = f"{type(e).__name__}: {e}"
                if attempt < 3:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise EmbeddingUnavailable(f"{self.model}: {last}") from e
        raise EmbeddingUnavailable(last)

    def _request(self, text: str, task: str) -> dict:
        return {
            "model": f"models/{self.model}",
            "content": {"parts": [{"text": text}]},
            "taskType": task,
            "outputDimensionality": self.dims,
        }

    def embed_documents(self, texts):
        out = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            res = self._call("batchEmbedContents",
                             {"requests": [self._request(t, "RETRIEVAL_DOCUMENT") for t in batch]})
            vecs = [e["values"] for e in res.get("embeddings", [])]
            if len(vecs) != len(batch):
                raise EmbeddingUnavailable(f"{self.model}: expected {len(batch)} embeddings, got {len(vecs)}")
            out.extend(_l2(v) for v in vecs)
        return out

    def embed_query(self, text):
        res = self._call("embedContent", self._request(text, "RETRIEVAL_QUERY"))
        return _l2(res["embedding"]["values"])


# --------------------------------------------------------------------------- selection
def build_embedders(config, api_key: str = None):
    """Return (primary, fallback_or_None) according to config."""
    icfg = config.section("ingestion")
    dims = int(icfg.get("embedding_dims", 768))
    choice = str(icfg.get("embedder", "auto")).lower()
    gem = GeminiEmbedder(model=config.get("gemini.embed_model", "gemini-embedding-001"), dims=dims,
                         batch_size=icfg.get("embed_batch_size", 50), api_key=api_key)
    local = LocalHashEmbedder(dims=dims)
    if choice == "local":
        return local, None
    if choice == "gemini":
        return gem, (local if icfg.get("fallback_to_local", True) else None)
    if choice == "auto":
        if gem.available():
            return gem, (local if icfg.get("fallback_to_local", True) else None)
        return local, None
    # any plugin-registered embedder name
    from .registry import create
    custom = create("embedder", choice, dims=dims, api_key=api_key)
    return custom, (local if icfg.get("fallback_to_local", True) and choice != "local" else None)
