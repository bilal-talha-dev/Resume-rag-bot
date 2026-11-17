"""Small text helpers shared by both pipelines (no resume-specific knowledge here)."""
import hashlib
import re

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "in", "on", "at", "to", "for", "with", "by", "from", "of", "and", "or",
    "what", "where", "when", "who", "whom", "which", "how", "why", "did",
    "does", "do", "has", "have", "had", "he", "his", "him", "she", "her", "hers",
    "they", "their", "i", "my", "me", "you", "your", "tell", "about", "can",
    "could", "would", "should", "resume", "resumes", "cv", "candidate", "candidates",
    "any", "all", "that", "this", "these", "those", "it", "its", "as", "me", "show",
}


def stem(tok: str) -> str:
    tok = tok.lower().replace("'s", "")
    if len(tok) > 5 and tok.endswith("ies"):
        return tok[:-3] + "y"
    for suf in ("ing", "ed", "es", "s"):
        if len(tok) > len(suf) + 3 and tok.endswith(suf):
            return tok[: -len(suf)]
    return tok


def tokenize(text: str, stopwords=STOPWORDS) -> list[str]:
    """Lowercase tokens that keep tech names intact (c++, c#, node.js, ci/cd)."""
    cleaned = re.sub(r"[^a-z0-9+#.\-/]", " ", text.lower())
    out = []
    for t in cleaned.split():
        t = t.strip(".-/")
        if len(t) < 2 or t in stopwords:
            continue
        out.append(stem(t))
        if any(c in t for c in ".-/"):
            out.extend(stem(s) for s in re.split(r"[.\-/]", t) if len(s) > 1 and s not in stopwords)
    return out


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].strip("-") or "candidate"


def sha256_file(path: str, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def sha1_text(text: str, n: int = 8) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]
