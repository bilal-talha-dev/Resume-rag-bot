"""Process-wide singletons: one workspace, one ingestion pipeline, one retrieval pipeline."""
import threading

from rag_core import build, load_config

_lock = threading.Lock()
_state = {}


def get():
    with _lock:
        if not _state:
            config = load_config()
            ingestion, retrieval = build(config)
            _state.update(config=config, ingestion=ingestion, retrieval=retrieval)
        return _state["config"], _state["ingestion"], _state["retrieval"]


def start_background_ingest():
    config, ingestion, _ = get()
    if not config.get("ingestion.auto_ingest_on_start", True):
        return

    def job():
        try:
            ingestion.run(verbose=True)
        except Exception as exc:  # never crash the server because of warm-up
            print(f"[auto-ingest] failed: {exc}")

    threading.Thread(target=job, daemon=True, name="auto-ingest").start()
