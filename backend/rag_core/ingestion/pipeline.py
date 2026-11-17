"""
INGESTION PIPELINE
==================
    discover -> diff -> [load -> parse -> chunk] (parallel) -> embed (batched) -> store -> manifest

* Works on any number of resumes (1, 40, 50, 500...): drop files into `paths.resumes_dir`, run `ingest()`.
* Incremental: unchanged files are skipped; changed files are re-indexed; deleted files are removed.
* Fault-tolerant: one unreadable resume is reported as 'failed' and never stops the rest.
* Every stage is replaceable through the registry (see rag_core/registry.py + rag_config.yaml).
"""
import hashlib
import json
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import registry
from ..embeddings import build_embedders
from ..text_utils import sha1_text, sha256_file, slugify
from ..types import EmbeddingUnavailable, SourceFile
from ..workspace import Workspace
from . import chunkers, loaders, parsers  # noqa: F401  (registers the built-in components)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class IngestionPipeline:
    def __init__(self, workspace: Workspace, log=print):
        self.ws = workspace
        self.config = workspace.config
        self.log = log
        self._run_lock = threading.Lock()
        self.status = {"state": "idle", "stage": "", "done": 0, "total": 0, "current": "",
                       "started_at": None, "finished_at": None, "report": None}

    # ------------------------------------------------------------------ helpers
    def _fingerprint(self) -> str:
        """Hash of every setting that changes what gets indexed -> editing config re-indexes files."""
        i = self.config.section("ingestion")
        keep = {k: i.get(k) for k in ("parser", "candidate_name_source", "section_aliases",
                                      "detect_unknown_headers", "chunker", "chunk")}
        return hashlib.sha1(json.dumps(keep, sort_keys=True, default=str).encode()).hexdigest()[:10]

    def _set(self, **kw):
        self.status.update(kw)

    # ---------------------------------------------------------------- stage 0: discover
    def discover(self) -> list[SourceFile]:
        icfg = self.config.section("ingestion")
        exts = {e.lower() for e in icfg.get("extensions", [])}
        max_bytes = float(icfg.get("max_file_mb", 15)) * 1024 * 1024
        root = self.ws.resumes_dir
        walker = os.walk(root) if icfg.get("recursive", True) else [(str(root), [], os.listdir(root))]
        out = []
        for dirpath, _dirs, files in walker:
            for fn in sorted(files):
                if fn.startswith(".") or os.path.splitext(fn)[1].lower() not in exts:
                    continue
                ap = os.path.join(dirpath, fn)
                size = os.path.getsize(ap)
                rel = os.path.relpath(ap, root).replace(os.sep, "/")
                if size > max_bytes:
                    out.append(SourceFile(rel, ap, size, ""))   # flagged later as too large
                    continue
                out.append(SourceFile(rel, ap, size, sha256_file(ap)))
        return sorted(out, key=lambda s: s.rel_path)

    # ------------------------------------------------------------------ stages 1-3
    def _process_file(self, src: SourceFile, parser, chunker):
        if not src.sha256:
            raise ValueError(f"file larger than ingestion.max_file_mb")
        text = loaders.load_file(src.abs_path)
        parsed = parser.parse(text, src.rel_path)
        candidate_id = f"{slugify(parsed.name)}-{sha1_text(src.rel_path, 4)}"
        chunks = chunker.chunk(parsed, candidate_id)
        if not chunks:
            raise ValueError("no chunks produced")
        profile = {"candidate_id": candidate_id, "name": parsed.name, "email": parsed.email,
                   "phone": parsed.phone, "links": parsed.links, "headline": parsed.headline,
                   "sections": [s for s, _ in parsed.sections]}
        return parsed, profile, chunks

    # ------------------------------------------------------------------- public
    def run(self, force: bool = False, api_key: str = None, only: list = None, verbose: bool = True) -> dict:
        """Ingest everything (or only the given relative paths). Thread-safe; one run at a time."""
        if not self._run_lock.acquire(blocking=False):
            return {"error": "an ingestion run is already in progress", "status": self.status}
        try:
            self._set(state="running", stage="discover", done=0, total=0, current="",
                      started_at=_now(), finished_at=None, report=None)
            t0 = time.time()
            primary, fallback = build_embedders(self.config, api_key)
            warnings = []
            try:
                report = self._run_with(primary, force, only, verbose)
            except EmbeddingUnavailable as e:
                if not fallback:
                    raise
                warnings.append(f"{primary.id} unavailable ({e}); indexed with offline embedder '{fallback.id}' instead")
                if verbose:
                    self.log(f"  [WARN] {warnings[-1]}")
                report = self._run_with(fallback, force, only, verbose)
            report["warnings"] = warnings + report.get("warnings", [])
            report["total_time_s"] = round(time.time() - t0, 2)
            self._set(state="done", stage="", finished_at=_now(), report=report)
            return report
        except Exception as e:
            self._set(state="error", finished_at=_now(), report={"error": f"{type(e).__name__}: {e}"})
            raise
        finally:
            self._run_lock.release()

    def _run_with(self, embedder, force, only, verbose) -> dict:
        icfg = self.config.section("ingestion")
        store = self.ws.store_for(embedder.id)
        manifest = self.ws.manifest
        manifest.reload()
        known = manifest.entries(embedder.id)
        fp = self._fingerprint()
        incremental = icfg.get("incremental", True) and store.persistent and not force

        sources = self.discover()
        if only:
            sources = [s for s in sources if s.rel_path in set(only)]
        present = {s.rel_path for s in sources}

        todo, skipped, failed, ok = [], [], [], []
        for s in sources:
            e = known.get(s.rel_path)
            same = e and e.get("sha256") == s.sha256 and e.get("fingerprint") == fp and e.get("status") == "ok"
            (skipped if incremental and same else todo).append(s)

        deleted = []
        if icfg.get("delete_missing", True) and not only:
            deleted = [p for p in known if p not in present]

        if verbose:
            self.log(f"\n== INGESTION  embedder={embedder.id}  store={store.name}")
            self.log(f"   found {len(sources)} file(s): {len(todo)} to ingest, {len(skipped)} unchanged, {len(deleted)} removed")

        # ---- stages 1-3 in parallel
        self._set(stage="load/parse/chunk", total=len(todo), done=0)
        parser = registry.create("parser", icfg.get("parser", "resume"), self.config)
        chunker = registry.create("chunker", icfg.get("chunker", "section"), self.config)
        processed = []

        def work(src):
            try:
                self._set(current=src.rel_path)
                return src, self._process_file(src, parser, chunker), None
            except Exception as e:
                return src, None, f"{type(e).__name__}: {e}"

        with ThreadPoolExecutor(max_workers=max(1, int(icfg.get("workers", 4)))) as ex:
            for n, (src, res, err) in enumerate(ex.map(work, todo), 1):
                self._set(done=n)
                if err:
                    failed.append({"source": src.rel_path, "error": err})
                    store.delete({"source": src.rel_path})      # never leave stale chunks of a broken file
                    manifest.set_entry(embedder.id, src.rel_path, {
                        "sha256": src.sha256, "fingerprint": fp, "status": "failed", "error": err, "ingested_at": _now()})
                    if verbose:
                        self.log(f"   ✗ {src.rel_path}: {err}")
                else:
                    processed.append((src, *res))
                    if verbose:
                        self.log(f"   ✓ parsed {src.rel_path} -> {res[1]['name']} ({len(res[2])} chunks)")

        # ---- stage 4: embed ALL chunks of ALL files together (few, large batches)
        all_chunks = [c for _src, _parsed, _profile, chunks in processed for c in chunks]
        self._set(stage="embed", done=0, total=len(all_chunks), current="")
        t_embed = time.time()
        vectors = embedder.embed_documents([c.text for c in all_chunks]) if all_chunks else []
        embed_time = round(time.time() - t_embed, 2)
        if verbose and all_chunks:
            self.log(f"   embedded {len(all_chunks)} chunks in {embed_time}s with {embedder.id}")

        # ---- stage 5: store (replace each file's old chunks), then update manifest
        self._set(stage="store", done=0, total=len(processed))
        pos = 0
        for n, (src, _parsed, profile, chunks) in enumerate(processed, 1):
            vecs = vectors[pos:pos + len(chunks)]
            pos += len(chunks)
            store.delete({"source": src.rel_path})
            store.upsert([c.id for c in chunks], [c.text for c in chunks],
                         [c.metadata() for c in chunks], vecs)
            manifest.set_entry(embedder.id, src.rel_path, {
                "sha256": src.sha256, "fingerprint": fp, "status": "ok", "profile": profile,
                "chunks": len(chunks), "ingested_at": _now()})
            ok.append({"source": src.rel_path, "candidate": profile["name"], "chunks": len(chunks)})
            self._set(done=n)

        for rel in deleted:
            store.delete({"source": rel})
            manifest.remove_entry(embedder.id, rel)
        manifest.save()

        total_in_store = store.count()
        if verbose:
            self.log(f"   ✓ stored {len(all_chunks)} new chunk(s) across {len(ok)} resume(s) in {store.name} — {total_in_store} total chunks ready")

        return {
            "embedder": embedder.id,
            "vector_db": store.name,
            "collection": getattr(store, "collection_name", None),
            "files_found": len(sources),
            "ingested": len(ok),
            "skipped_unchanged": len(skipped),
            "failed": len(failed),
            "removed": len(deleted),
            "chunks_added": len(all_chunks),
            "total_chunks_in_store": total_in_store,
            "embed_time_s": embed_time,
            "results": ok,
            "failures": failed,
            "removed_sources": deleted,
        }

    # ------------------------------------------------------------- maintenance
    def remove(self, source: str, delete_file: bool = True, api_key: str = None) -> bool:
        """Remove one resume from the index (and optionally from disk) across all embedders."""
        removed = False
        for eid in self.ws.manifest.embedder_ids():
            if source in self.ws.manifest.entries(eid):
                self.ws.store_for(eid).delete({"source": source})
                self.ws.manifest.remove_entry(eid, source)
                removed = True
        self.ws.manifest.save()
        path = self.ws.resumes_dir / source
        if delete_file and path.exists() and path.resolve().is_relative_to(self.ws.resumes_dir.resolve()):
            path.unlink()
            removed = True
        return removed
