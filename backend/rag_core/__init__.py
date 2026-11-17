"""
rag_core — two independent, configurable pipelines over a shared workspace.

    from rag_core import build
    ingest, retrieve = build()
    ingest.run()                       # index every resume in resumes/
    retrieve.query("Who knows Terraform?")
"""
import importlib

from .config import Config, load_config
from .workspace import Workspace
from .ingestion.pipeline import IngestionPipeline
from .retrieval.pipeline import RetrievalPipeline
from .types import EmbeddingUnavailable, NothingIndexed  # noqa: F401


def load_plugins(config: Config):
    for mod in config.get("plugins", []) or []:
        importlib.import_module(mod)


def build(config: Config = None, log=print):
    config = config or load_config()
    load_plugins(config)
    ws = Workspace(config)
    return IngestionPipeline(ws, log=log), RetrievalPipeline(ws, log=log)
