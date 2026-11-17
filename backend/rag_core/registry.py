"""
Component registry — this is what makes every stage swappable.

    from rag_core.registry import register

    @register("chunker", "my_chunker")
    class MyChunker: ...

then set `ingestion.chunker: my_chunker` in rag_config.yaml.
Kinds in use: loader, parser, chunker, embedder, store, reranker, generator.
"""
_REGISTRY: dict[str, dict[str, type]] = {}


def register(kind: str, name: str):
    def deco(cls):
        _REGISTRY.setdefault(kind, {})[name] = cls
        cls.registry_name = name
        return cls
    return deco


def get(kind: str, name: str):
    try:
        return _REGISTRY[kind][name]
    except KeyError:
        known = ", ".join(sorted(_REGISTRY.get(kind, {}))) or "(none)"
        raise KeyError(f"No {kind} named '{name}'. Registered {kind}s: {known}") from None


def available(kind: str) -> list[str]:
    return sorted(_REGISTRY.get(kind, {}))


def create(kind: str, name: str, *args, **kwargs):
    return get(kind, name)(*args, **kwargs)
