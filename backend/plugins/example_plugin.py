"""
Example plugin — shows how to swap or add pipeline components WITHOUT touching rag_core.

1. Uncomment / edit what you need below.
2. In rag_config.yaml set:
       plugins: ["plugins.example_plugin"]
       ingestion: { chunker: my_chunker }
       retrieval: { reranker: boost_recent }
"""
from rag_core.ingestion.chunkers import BaseChunker, _make
from rag_core.registry import register


@register("chunker", "my_chunker")
class WholeResumeChunker(BaseChunker):
    """One chunk per resume (fine for short resumes; loses fine-grained retrieval)."""

    def chunk(self, parsed, candidate_id):
        return [_make(parsed, candidate_id, "RESUME", "", parsed.raw_text.split("\n"), 0)]


@register("reranker", "boost_recent")
class BoostPresent:
    """Reorders hybrid-search results: chunks mentioning 'Present' (current jobs) get a small boost."""

    def __init__(self, config):
        self.config = config

    def rerank(self, query, ranked):
        for r in ranked:
            if "present" in r["text"].lower():
                r["score"] = round(r["score"] * 1.15, 4)
        return sorted(ranked, key=lambda r: r["score"], reverse=True)


# Custom embedder skeleton (e.g. OpenAI / sentence-transformers). Its `id` decides the Chroma collection name.
# from rag_core.embeddings import BaseEmbedder
# @register("embedder", "my_embedder")
# class MyEmbedder(BaseEmbedder):
#     provider, model, dims = "mine", "v1", 384
#     def __init__(self, **kw): ...
#     def embed_documents(self, texts): return [...]
