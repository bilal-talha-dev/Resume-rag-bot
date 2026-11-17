"""
Workspace = the only thing the two pipelines share:
  * config
  * a manifest (what was ingested, per embedder)  -> the retrieval side's "table of contents"
  * vector store handles
"""
import json
import os
import threading
import time
from pathlib import Path

from .store import create_store


class Manifest:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.RLock()
        self._data = {}
        self._mtime = None
        self._counter = 0
        self.reload()

    def reload(self):
        with self._lock:
            try:
                st = self.path.stat()
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                self._mtime = st.st_mtime_ns
            except FileNotFoundError:
                self._data, self._mtime = {}, None
            except Exception:
                self._data, self._mtime = {}, None

    def refresh_if_changed(self):
        try:
            m = self.path.stat().st_mtime_ns
        except FileNotFoundError:
            m = None
        if m != self._mtime:
            self.reload()

    @property
    def revision(self):
        self.refresh_if_changed()
        return (self._mtime, self._counter)

    def entries(self, embedder_id: str) -> dict:
        with self._lock:
            return dict(self._data.get(embedder_id, {}))

    def embedder_ids(self) -> list:
        with self._lock:
            return list(self._data.keys())

    def set_entry(self, embedder_id: str, source: str, entry: dict):
        with self._lock:
            self._data.setdefault(embedder_id, {})[source] = entry

    def remove_entry(self, embedder_id: str, source: str):
        with self._lock:
            self._data.get(embedder_id, {}).pop(source, None)

    def save(self):
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=1, ensure_ascii=False)
            os.replace(tmp, self.path)
            self._counter += 1
            try:
                self._mtime = self.path.stat().st_mtime_ns
            except FileNotFoundError:
                pass


class Workspace:
    def __init__(self, config):
        self.config = config
        self.manifest = Manifest(config.path("data_dir") / "manifest.json")
        self._stores = {}
        self._lock = threading.Lock()
        self.resumes_dir = config.path("resumes_dir")
        self.resumes_dir.mkdir(parents=True, exist_ok=True)

    def store_for(self, embedder_id: str):
        with self._lock:
            if embedder_id not in self._stores:
                self._stores[embedder_id] = create_store(self.config, embedder_id)
            return self._stores[embedder_id]

    def candidates(self, embedder_id: str) -> list[dict]:
        out = []
        for source, e in self.manifest.entries(embedder_id).items():
            if e.get("status") == "ok":
                out.append({"source": source, **e.get("profile", {}), "chunks": e.get("chunks", 0),
                            "ingested_at": e.get("ingested_at")})
        return sorted(out, key=lambda c: c.get("name", "").lower())
