"""
RETRIEVAL PIPELINE
==================
    understand -> search (vector + BM25) -> rank -> select candidates -> build context -> generate

Two scopes, chosen automatically (or forced with options):
  * candidate scope — the question names someone ("Tell me about Ali Khan") -> only that resume is searched and
    the WHOLE resume is sent to the LLM (most accurate).
  * pool scope      — "Who knows Terraform?" -> best chunks across ALL resumes, grouped per candidate so one
    resume can't crowd out the others; top `candidate_limit` candidates are sent to the LLM.
"""
import re
import time

import numpy as np

from .. import registry
from ..embeddings import build_embedders, resolve_api_key
from ..text_utils import tokenize
from ..types import EmbeddingUnavailable, NothingIndexed
from ..workspace import Workspace
from . import generator as _generator  # noqa: F401  (registers built-in generators)
from .generator import extractive_answer
from .index import RetrievalIndex

PRONOUN_RE = re.compile(r"\b(he|his|him|she|her|hers|they|their|them|this candidate|that candidate|the candidate)\b", re.I)

DEFAULT_SYSTEM_PROMPT = """You are an AI recruiting assistant working over a database of {total} resumes. Today's date is {today}.

The RESUME CONTEXT below holds {shown} candidate(s) that were selected as the most relevant to the question (out of {total} resumes in the database). It is the single source of truth.

How to answer:
1. Answer exactly what was asked, directly and naturally. Read ALL of the context before deciding something is missing.
2. Attribute every fact to the correct candidate BY NAME. Never mix details of different candidates.
3. You may reason over the context: list, count, compare, rank candidates for a role, compute durations, summarise, or draft a short bio / pitch — as long as it is grounded in the context. When ranking or recommending, justify each pick with concrete evidence from that candidate's resume.
4. Never invent employers, dates, numbers, skills or achievements. If something isn't in the resume (salary, age, marital status, ...), say so in one sentence and offer the closest facts you do have.
5. For questions about the whole pool ("who has X", "how many have Y") you only see the top matches; say so if the answer could be incomplete, and mention that the user can raise the candidate limit.
6. Use the conversation history to resolve follow-ups ("he", "that company", "the second one").
7. Greetings / small talk: reply briefly and say what you can help with. General non-resume questions: answer briefly and say it is general knowledge.
8. Format: concise Markdown; bullets for lists, **bold** for names and key facts. Do not paste raw [bracketed] headers or chunk ids."""


def _format_history(history, max_turns=6, max_chars=500) -> str:
    lines = []
    for m in (history or [])[-max_turns:]:
        role = "User" if m.get("role") == "user" else "Assistant"
        content = str(m.get("content", "")).strip().replace("\n", " ")
        if content:
            lines.append(f"{role}: {content[:max_chars]}")
    return "\n".join(lines)


class RetrievalPipeline:
    def __init__(self, workspace: Workspace, log=print):
        self.ws = workspace
        self.config = workspace.config
        self.log = log
        self._index_cache = {}
        self._generators = {}

    # ------------------------------------------------------------------ backend
    def _resolve(self, api_key):
        """Pick the embedder whose collection actually holds data. Returns (embedder|None, embedder_id)."""
        primary, fallback = build_embedders(self.config, api_key)
        for emb in (primary, fallback):
            if emb is not None and self.ws.candidates(emb.id):
                return emb, emb.id
        for eid in self.ws.manifest.embedder_ids():      # data exists but we can't embed queries for it
            if self.ws.candidates(eid):
                return None, eid
        raise NothingIndexed("No resumes are indexed yet. Add files to the resumes folder and run ingestion.")

    def _index(self, embedder_id) -> RetrievalIndex:
        rev = self.ws.manifest.revision
        cached = self._index_cache.get(embedder_id)
        if cached and cached[0] == rev:
            return cached[1]
        data = self.ws.store_for(embedder_id).get()
        index = RetrievalIndex(data["ids"], data["documents"], data["metadatas"], self.ws.candidates(embedder_id))
        self._index_cache[embedder_id] = (rev, index)
        return index

    # ------------------------------------------------------------------ helpers
    def _expand(self, query: str, synonyms) -> list[str]:
        raw = set(re.findall(r"[a-z0-9+#.\-/']+", query.lower()))
        raw |= {r.strip(".-/'") for r in raw}
        extra = []
        for rule in synonyms or []:
            if raw & set(rule.get("when", [])):
                extra.extend(rule.get("add", "").split())
        return tokenize(query) + tokenize(" ".join(dict.fromkeys(extra)))

    def _generator(self):
        name = self.config.get("generation.generator", "gemini")
        if name not in self._generators:
            self._generators[name] = registry.create("generator", name, self.config)
        return self._generators[name]

    # --------------------------------------------------------------------- main
    def query(self, user_query: str, history: list = None, api_key: str = None,
              options: dict = None, verbose: bool = True) -> dict:
        t_start = time.time()
        rcfg = {**self.config.section("retrieval"), **{k: v for k, v in (options or {}).items() if v is not None}}
        api_key = resolve_api_key(api_key)
        history = [m for m in (history or []) if isinstance(m, dict)]

        embedder, eid = self._resolve(api_key)
        index = self._index(eid)
        store = self.ws.store_for(eid)
        total_candidates = len(index.candidates)

        # ---------------- STAGE A: understand the question
        retrieval_query = user_query
        pronoun = bool(PRONOUN_RE.search(user_query))
        prev_users = [str(m["content"]) for m in history if m.get("role") == "user" and m.get("content")]
        matched = []
        explicit = rcfg.get("candidates")
        if explicit:
            wanted = {str(x).lower() for x in explicit}
            matched = [cid for cid, c in index.candidates.items()
                       if cid.lower() in wanted or c.get("name", "").lower() in wanted or c.get("source", "").lower() in wanted]
        elif rcfg.get("candidate_detection", True):
            matched = index.detect_candidates(user_query)
            if not matched and prev_users and (pronoun or len(tokenize(user_query)) <= 3):
                for prev in reversed(prev_users[-3:]):          # follow-up: "his email?" -> last named person
                    matched = index.detect_candidates(prev)
                    if matched:
                        break
        if prev_users and (len(tokenize(user_query)) <= 3 or (pronoun and not index.detect_candidates(user_query))):
            retrieval_query = f"{prev_users[-1]} {user_query}"
        scope = "candidate" if matched else "pool"
        allowed = {n for cid in matched for n in index.by_candidate.get(cid, [])} if matched else None

        # ---------------- STAGE B: hybrid search
        terms = self._expand(retrieval_query, rcfg.get("synonyms"))
        fetch_k = int(rcfg.get("fetch_k", 80))
        lex = index.bm25.scores(terms, allowed)

        q_vec, q_err, t_emb = None, None, 0.0
        if embedder is not None and embedder.available():
            t0 = time.time()
            try:
                q_vec = embedder.embed_query(retrieval_query)
            except EmbeddingUnavailable as e:
                q_err = str(e)
            t_emb = round(time.time() - t0, 3)
        elif embedder is not None:
            q_err = "no embedding API key — keyword-only retrieval"

        sem = {}
        if q_vec is not None:
            where = {"candidate_id": {"$in": matched}} if matched else None
            n_sem = len(allowed) if allowed is not None else fetch_k
            for cid_, s in store.query(q_vec, n_sem, where):
                if cid_ in index.pos:
                    sem[index.pos[cid_]] = s
            top_lex = sorted(lex, key=lex.get, reverse=True)[:fetch_k]
            missing = [i for i in top_lex if i not in sem]
            if missing:                                    # lexical-only hits still need a vector score
                got = store.get(ids=[index.ids[i] for i in missing], embeddings=True)
                qv = np.asarray(q_vec, dtype=float)
                for gid, emb in zip(got["ids"], got["embeddings"]):
                    e = np.asarray(emb, dtype=float)
                    den = (np.linalg.norm(qv) * np.linalg.norm(e)) or 1.0
                    sem[index.pos[gid]] = max(0.0, float(qv @ e / den))

        w = rcfg.get("weights", {"semantic": 0.55, "keyword": 0.45})
        w_sem, w_lex = (w.get("semantic", 0.55), w.get("keyword", 0.45)) if q_vec is not None else (0.0, 1.0)
        lex_max = max(lex.values()) if lex else 1.0
        universe = allowed if allowed is not None else (set(sem) | set(sorted(lex, key=lex.get, reverse=True)[:fetch_k]))
        ranked = []
        for i in universe:
            cs, kw = sem.get(i, 0.0), (lex.get(i, 0.0) / lex_max if lex_max else 0.0)
            m = index.metas[i]
            ranked.append({"id": index.ids[i], "idx": i, "candidate_id": m["candidate_id"],
                           "candidate_name": m["candidate_name"], "section": m["section"], "entry": m.get("entry", ""),
                           "text": index.docs[i], "score": round(w_sem * cs + w_lex * kw, 4),
                           "cosine": round(cs, 4), "keyword": round(kw, 4)})
        ranked.sort(key=lambda r: r["score"], reverse=True)

        rr_name = rcfg.get("reranker", "none")
        if rr_name and rr_name != "none":
            ranked = registry.create("reranker", rr_name, self.config).rerank(retrieval_query, ranked)

        # ---------------- STAGE C: choose candidates + chunks for the LLM
        cand_limit = max(1, int(rcfg.get("candidate_limit", 6)))
        per_cand = max(1, int(rcfg.get("max_chunks_per_candidate", 4)))
        budget = int(rcfg.get("context_max_chars", 16000))
        by_cand: dict[str, list[dict]] = {}
        for r in ranked:
            by_cand.setdefault(r["candidate_id"], []).append(r)

        def cand_score(rows):  # best chunk counts most, a couple of supporting chunks add a bit
            s = [r["score"] for r in rows]
            return s[0] + 0.3 * sum(s[1:3])

        order = sorted(by_cand, key=lambda c: cand_score(by_cand[c]), reverse=True)
        if scope == "pool":
            order = [c for c in order if by_cand[c][0]["score"] > 0]
        order = order[:cand_limit]
        if scope == "candidate":                               # keep matched people even if some had no hits
            order = (order + [c for c in matched if c not in order])[:cand_limit]

        mode = "profile" if (scope == "candidate" and rcfg.get("profile_mode", True)) else "retrieved"
        per_budget = budget // max(1, len(order))
        score_of = {r["id"]: r["score"] for r in ranked}
        groups = []
        for cid in order:
            if mode == "profile":
                chunk_idx = list(index.by_candidate[cid])
            else:
                chosen = [r["idx"] for r in by_cand.get(cid, [])[:per_cand]]
                hdr = index.header_chunk(cid)
                if hdr is not None and hdr not in chosen:
                    chosen.append(hdr)
                chunk_idx = sorted(chosen, key=lambda n: index.metas[n].get("chunk_index", 0))
            # trim to this candidate's character budget, dropping the lowest-scoring chunks first
            while sum(len(index.docs[n]) for n in chunk_idx) > per_budget and len(chunk_idx) > 1:
                drop = min((n for n in chunk_idx if index.metas[n].get("section") != "HEADER"),
                           key=lambda n: score_of.get(index.ids[n], 0.0), default=None)
                if drop is None:
                    break
                chunk_idx.remove(drop)
            cand = index.candidates[cid]
            groups.append({"candidate_id": cid, "name": cand.get("name", cid), "source": cand.get("source", ""),
                           "email": cand.get("email", ""), "phone": cand.get("phone", ""),
                           "score": round(cand_score(by_cand[cid]), 4) if cid in by_cand else 0.0,
                           "chunks": [{"id": index.ids[n], "section": index.metas[n]["section"],
                                       "text": index.docs[n], "score": score_of.get(index.ids[n], 0.0)} for n in chunk_idx]})

        # ---------------- STAGE D: assemble the prompt
        blocks = []
        for g in groups:
            contact = " | ".join(x for x in (f"Email: {g['email']}" if g["email"] else "",
                                             f"Phone: {g['phone']}" if g["phone"] else "") if x)
            head = f"### CANDIDATE: {g['name']}  (file: {g['source']})" + (f"\n{contact}" if contact else "")
            blocks.append(head + "\n" + "\n\n".join(c["text"] for c in g["chunks"]))
        context = "\n\n".join(blocks) if blocks else "(no relevant resume content found)"
        system = self.config.get("generation.system_prompt") or DEFAULT_SYSTEM_PROMPT
        system = (system.replace("{today}", time.strftime("%B %d, %Y")).replace("{total}", str(total_candidates))
                  .replace("{shown}", str(len(groups))))
        prompt = (f"{system}\n\nRESUME CONTEXT:\n{context}\n\nCONVERSATION HISTORY:\n"
                  f"{_format_history(history, rcfg.get('history_turns', 6)) or '(none)'}\n\nUSER QUESTION:\n{user_query}\n")

        # ---------------- STAGE E: generate
        answer, used_model, gen_time, attempts, llm_error = None, None, 0.0, [], None
        if api_key:
            res = self._generator().generate(prompt, api_key, verbose)
            answer, used_model, gen_time, attempts, llm_error = (res["text"], res["model"], res["latency_s"],
                                                                  res["attempts"], res["error"])
        else:
            llm_error = "no GEMINI_API_KEY configured"
        if not answer:
            t0 = time.time()
            answer = extractive_answer(user_query, groups, total_candidates, llm_error if api_key else None)
            gen_time = round(time.time() - t0, 3)
            used_model = "extractive-fallback" + (" (Gemini unavailable)" if api_key else " (set GEMINI_API_KEY)")
            attempts.append({"model": "extractive-fallback", "status": "SUCCESS", "latency_s": gen_time})

        selected = [{**c, "section": c["section"], "candidate_name": g["name"]} for g in groups for c in g["chunks"]]
        selected.sort(key=lambda c: c["score"], reverse=True)
        top = ranked[0] if ranked else None
        if verbose:
            self.log(f"[retrieve] scope={scope} mode={mode} matched={len(matched)} candidates_sent={len(groups)}/{total_candidates} "
                     f"chunks={len(selected)} model={used_model} total={time.time() - t_start:.2f}s")

        return {
            "query": user_query,
            "retrieval_query": retrieval_query,
            "answer": answer.strip(),
            "used_model": used_model,
            "scope": scope,
            "context_mode": mode,
            "total_candidates": total_candidates,
            "matched_candidates": [index.candidates[c].get("name", c) for c in matched],
            "candidates": [{"candidate_id": g["candidate_id"], "name": g["name"], "source": g["source"],
                            "score": g["score"], "chunks_used": len(g["chunks"])} for g in groups],
            "vector_db": store.name,
            "chroma_collection": getattr(store, "collection_name", None),
            "embedding_model": embedder.id if (embedder is not None and q_vec is not None) else "keyword-only",
            "embedding_error": q_err,
            "llm_error": llm_error,
            "context_chunk_ids": [c["id"] for c in selected],
            "query_embed_time_s": t_emb,
            "generation_time_s": gen_time,
            "total_time_s": round(time.time() - t_start, 3),
            "top_match": {k: v for k, v in top.items() if k != "idx"} if top else None,
            "selected_chunks": selected,
            "ranked_matches": [{k: v for k, v in r.items() if k != "idx"} for r in ranked[:30]],
            "injected_prompt": prompt,
            "model_attempts": attempts,
            "query_vector_sample": [round(x, 4) for x in (q_vec or [])[:4]],
            "query_vector_dims": len(q_vec or []),
        }

    def list_chunks(self, candidate_id: str = None, limit: int = 300, api_key: str = None) -> dict:
        embedder, eid = self._resolve(resolve_api_key(api_key))
        index = self._index(eid)
        idxs = index.by_candidate.get(candidate_id, []) if candidate_id else range(index.size)
        rows = [{"id": index.ids[n], "candidate_id": index.metas[n]["candidate_id"],
                 "candidate_name": index.metas[n]["candidate_name"], "section": index.metas[n]["section"],
                 "text": index.docs[n]} for n in list(idxs)[:limit]]
        return {"total_chunks": index.size, "returned": len(rows), "chunks": rows, "embedder": eid}
