"""Answer generation. `gemini` calls the LLM (with model fallback); `extractive` is the no-LLM safety net."""
import json
import re
import time
import urllib.error

from ..embeddings import _http_error_detail, gemini_post
from ..registry import register

_DISCOVERED = {"t": 0.0, "models": []}


def discover_flash_models(api_key: str) -> list[str]:
    """Ask Google which flash models this key can call (cached 1h)."""
    import urllib.request
    if time.time() - _DISCOVERED["t"] < 3600 and _DISCOVERED["models"]:
        return _DISCOVERED["models"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models?pageSize=200&key={api_key}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    found = []
    for m in data.get("models", []):
        name = m.get("name", "").replace("models/", "")
        if "flash" not in name or "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if re.search(r"image|tts|audio|live|native|robotics|computer|embedding|exp", name):
            continue
        ver = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
        found.append((-(float(ver.group(1)) if ver else 0), "lite" in name, name))
    models = [n for _, _, n in sorted(found)]
    if models:
        _DISCOVERED.update(t=time.time(), models=models)
    return models


@register("generator", "gemini")
class GeminiGenerator:
    def __init__(self, config):
        g = config.section("generation")
        self.models = list(g.get("models", []))
        self.temperature = g.get("temperature", 0.3)
        self.timeout = int(g.get("timeout_s", 40))
        self._good = None
        self._dead = set()

    def _try(self, models, payload, api_key, verbose, attempts, errors):
        for model in models:
            if model in self._dead:
                continue
            for try_no in (1, 2):
                t0 = time.time()
                try:
                    res = gemini_post(model, "generateContent", payload, api_key, timeout=self.timeout)
                    text = "".join(p.get("text", "") for p in res["candidates"][0]["content"]["parts"]).strip()
                    if not text:
                        raise ValueError("empty response")
                    el = round(time.time() - t0, 2)
                    attempts.append({"model": model, "status": "SUCCESS", "latency_s": el})
                    self._good = model
                    return text, model, el
                except urllib.error.HTTPError as e:
                    detail = _http_error_detail(e)
                    errors.append(f"{model}: {detail}")
                    attempts.append({"model": model, "status": f"HTTP {e.code}", "latency_s": round(time.time() - t0, 2)})
                    if e.code in (429, 500, 503) and try_no == 1:
                        time.sleep(1.0)
                        continue
                    if e.code in (400, 404) or "no longer available" in detail.lower():
                        self._dead.add(model)
                    break
                except Exception as e:
                    errors.append(f"{model}: {type(e).__name__}: {e}")
                    attempts.append({"model": model, "status": f"FAILED ({type(e).__name__})", "latency_s": round(time.time() - t0, 2)})
                    break
        return None, None, 0.0

    def generate(self, prompt: str, api_key: str, verbose: bool = False) -> dict:
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": self.temperature}}
        attempts, errors = [], []
        models = ([self._good] if self._good else []) + [m for m in self.models if m != self._good]
        text, used, el = self._try(models, payload, api_key, verbose, attempts, errors)
        if not text:
            extra = [m for m in discover_flash_models(api_key) if m not in models and m not in self._dead]
            text, used, el = self._try(extra[:4], payload, api_key, verbose, attempts, errors)
        return {"text": text, "model": used, "latency_s": el, "attempts": attempts,
                "error": None if text else ("; ".join(errors[-3:])[:400] or "no model available")}


GREETING_RE = re.compile(r"^\s*(hi|hello|hey|salam|assalam[^\s]*|good (morning|afternoon|evening)|yo|sup|thanks|thank you)\b", re.I)


def extractive_answer(query: str, groups: list[dict], total: int, llm_error: str = None) -> str:
    """No-LLM fallback: show the best-matching snippets per candidate. Generic — no hard-coded Q&A."""
    if GREETING_RE.match(query) and len(query.split()) <= 5:
        return (f"Hi! I can answer questions about the {total} resume(s) in the database — find people by skill, "
                "compare candidates, or look up one person's experience, education and contact details.")
    if not groups:
        return "I couldn't find anything relevant to that in the indexed resumes."
    parts = []
    for g in groups:
        snippets = []
        for c in g["chunks"]:
            body = re.sub(r"^\[[^\]]+\]\s*", "", c["text"])
            snippets.append(f"_{c['section'].title()}_\n" + "\n".join(f"• {p.strip()}" if not p.strip().startswith("•") else p.strip()
                                                                       for p in body.split("\n") if p.strip()))
        parts.append(f"**{g['name']}**\n" + "\n\n".join(snippets[:3]))
    note = "\n\n_The LLM wasn't used for this answer"
    note += f" ({llm_error})._" if llm_error else " — set GEMINI_API_KEY for full natural-language answers._"
    return "\n\n---\n\n".join(parts) + note
