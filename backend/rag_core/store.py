"""Vector store wrappers: PostgreSQL + pgvector (default), ChromaDB, and In-Memory."""
import json
import os
import re
import threading

from .registry import register

try:
    import chromadb
    CHROMA_AVAILABLE = True
except ImportError:  # pragma: no cover
    chromadb = None
    CHROMA_AVAILABLE = False

# Support either psycopg2 (psycopg2-binary) or psycopg (v3)
_PG_DRIVER = None
try:
    import psycopg2
    import psycopg2.extras
    _PG_DRIVER = "psycopg2"
except ImportError:
    try:
        import psycopg
        _PG_DRIVER = "psycopg"
    except ImportError:
        _PG_DRIVER = None


def collection_name(embedder_id: str) -> str:
    return ("resumes_" + re.sub(r"[^a-zA-Z0-9_-]", "_", embedder_id))[:200]


def _vec_literal(vec) -> str:
    """Format a numeric sequence as a pgvector literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{float(x):.7f}" for x in vec) + "]"


class BaseStore:
    persistent = True
    name = "base"

    def count(self) -> int: ...
    def upsert(self, ids, documents, metadatas, embeddings): ...
    def delete(self, where: dict): ...
    def query(self, vector, n: int, where: dict = None) -> list[tuple[str, float]]: ...
    def get(self, ids=None, where=None, embeddings=False) -> dict: ...


@register("store", "pgvector")
@register("store", "postgres")
@register("store", "postgresql")
class PostgresVectorStore(BaseStore):
    """
    PostgreSQL + pgvector store.
    - Automatically runs `CREATE EXTENSION IF NOT EXISTS vector;`
    - Uses native `vector(dims)` column + HNSW cosine index (`vector_cosine_ops`) + `<=>` operator.
    - If the PostgreSQL server does not have the `pgvector` C extension binary installed yet,
      gracefully falls back to `DOUBLE PRECISION[]` inside the same PostgreSQL database.
    """
    persistent = True
    name = "PostgreSQL + pgvector (HNSW)"
    _init_lock = threading.Lock()

    def __init__(self, config_or_dir, embedder_id: str, pg_config: dict = None):
        self.collection_name = collection_name(embedder_id)
        if hasattr(config_or_dir, "section"):
            pg = config_or_dir.section("postgres")
            dims = int(config_or_dir.get("ingestion.embedding_dims", 768))
        else:
            pg = pg_config or {}
            dims = int(pg.get("dims", 768))

        self.dims = dims
        raw_table = pg.get("table") or os.getenv("POSTGRES_TABLE") or "rag_chunks"
        self.table = re.sub(r"[^a-zA-Z0-9_]", "_", raw_table)
        self.index_type = (pg.get("index_type") or os.getenv("POSTGRES_INDEX_TYPE") or "hnsw").lower()
        self.dsn = self._build_dsn(pg)
        self._has_pgvector = True
        self._ensure_schema()

    @staticmethod
    def _build_dsn(pg: dict) -> str:
        url = (
            pg.get("url")
            or os.getenv("DATABASE_URL")
            or os.getenv("PGVECTOR_URL")
            or os.getenv("POSTGRES_URL")
        )
        if url:
            return url.strip()
        host = pg.get("host") or os.getenv("POSTGRES_HOST") or "localhost"
        port = pg.get("port") or os.getenv("POSTGRES_PORT") or 5432
        dbname = pg.get("dbname") or os.getenv("POSTGRES_DB") or "rag_db"
        user = pg.get("user") or os.getenv("POSTGRES_USER") or "postgres"
        password = pg.get("password") or os.getenv("POSTGRES_PASSWORD") or "postgres"
        return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

    def _connect(self):
        if _PG_DRIVER == "psycopg2":
            return psycopg2.connect(self.dsn)
        if _PG_DRIVER == "psycopg":
            return psycopg.connect(self.dsn)
        raise RuntimeError(
            "PostgreSQL driver not installed. Run: pip install psycopg2-binary pgvector"
        )

    def _try_create_database(self):
        """If the target database (e.g. rag_db) does not exist yet on the Postgres server, create it automatically."""
        m = re.match(r"^(postgresql://[^/]+/)([a-zA-Z0-9_\-]+)(\?.*)?$", self.dsn)
        if not m:
            return
        admin_dsn = m.group(1) + "postgres" + (m.group(3) or "")
        target_db = m.group(2)
        try:
            conn = psycopg2.connect(admin_dsn) if _PG_DRIVER == "psycopg2" else psycopg.connect(admin_dsn)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_db,))
                if not cur.fetchone():
                    cur.execute(f"CREATE DATABASE {target_db};")
                    print(f"  [pgvector] Created PostgreSQL database '{target_db}' automatically.")
            conn.close()
        except Exception:
            pass

    def _ensure_schema(self):
        with self._init_lock:
            try:
                conn = self._connect()
            except Exception as exc:
                if "does not exist" in str(exc).lower():
                    self._try_create_database()
                    conn = self._connect()
                else:
                    raise
            try:
                conn.autocommit = True
                with conn.cursor() as cur:
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                        self._has_pgvector = True
                        self.name = "PostgreSQL + pgvector (HNSW)"
                    except Exception as exc:
                        self._has_pgvector = False
                        self.name = "PostgreSQL (ARRAY cosine fallback — install pgvector extension for HNSW)"
                        print(f"  [WARN] pgvector extension not available on Postgres server ({exc}); using float8[] fallback.")

                    vec_col_type = f"vector({self.dims})" if self._has_pgvector else "DOUBLE PRECISION[]"
                    cur.execute(
                        f"""
                        CREATE TABLE IF NOT EXISTS {self.table} (
                            collection   TEXT NOT NULL,
                            id           TEXT NOT NULL,
                            source       TEXT NOT NULL DEFAULT '',
                            candidate_id TEXT NOT NULL DEFAULT '',
                            document     TEXT NOT NULL,
                            metadata     JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                            embedding    {vec_col_type},
                            PRIMARY KEY (collection, id)
                        );
                        """
                    )
                    cur.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_{self.table}_col_source ON {self.table} (collection, source);"
                    )
                    cur.execute(
                        f"CREATE INDEX IF NOT EXISTS idx_{self.table}_col_cand ON {self.table} (collection, candidate_id);"
                    )
                    if self._has_pgvector and self.index_type == "hnsw":
                        try:
                            cur.execute(
                                f"CREATE INDEX IF NOT EXISTS idx_{self.table}_emb_hnsw "
                                f"ON {self.table} USING hnsw (embedding vector_cosine_ops);"
                            )
                        except Exception:
                            pass
            finally:
                conn.close()

    def _where_clause(self, where: dict | None) -> tuple[str, list]:
        clauses = ["collection = %s"]
        params: list = [self.collection_name]
        for k, cond in (where or {}).items():
            col = k if k in ("source", "candidate_id", "id") else None
            if isinstance(cond, dict) and "$in" in cond:
                vals = list(cond["$in"])
                if not vals:
                    clauses.append("1 = 0")
                elif col:
                    clauses.append(f"{col} = ANY(%s)")
                    params.append(vals)
                else:
                    clauses.append(f"(metadata->>%s) = ANY(%s)")
                    params.extend([k, [str(v) for v in vals]])
            else:
                if col:
                    clauses.append(f"{col} = %s")
                    params.append(str(cond))
                else:
                    clauses.append("(metadata->>%s) = %s")
                    params.extend([k, str(cond)])
        return " AND ".join(clauses), params

    def count(self) -> int:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM {self.table} WHERE collection = %s;", (self.collection_name,))
                row = cur.fetchone()
                return int(row[0]) if row else 0
        finally:
            conn.close()

    def upsert(self, ids, documents, metadatas, embeddings):
        if not ids:
            return
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    for cid, doc, meta, emb in zip(ids, documents, metadatas, embeddings):
                        meta_dict = dict(meta or {})
                        source = str(meta_dict.get("source", ""))
                        cand_id = str(meta_dict.get("candidate_id", ""))
                        meta_json = json.dumps(meta_dict, ensure_ascii=False)
                        if self._has_pgvector:
                            vec_val = _vec_literal(emb)
                            cur.execute(
                                f"""
                                INSERT INTO {self.table} (collection, id, source, candidate_id, document, metadata, embedding)
                                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                                ON CONFLICT (collection, id) DO UPDATE SET
                                    source = EXCLUDED.source,
                                    candidate_id = EXCLUDED.candidate_id,
                                    document = EXCLUDED.document,
                                    metadata = EXCLUDED.metadata,
                                    embedding = EXCLUDED.embedding;
                                """,
                                (self.collection_name, cid, source, cand_id, doc, meta_json, vec_val),
                            )
                        else:
                            vec_list = [float(x) for x in emb]
                            cur.execute(
                                f"""
                                INSERT INTO {self.table} (collection, id, source, candidate_id, document, metadata, embedding)
                                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                                ON CONFLICT (collection, id) DO UPDATE SET
                                    source = EXCLUDED.source,
                                    candidate_id = EXCLUDED.candidate_id,
                                    document = EXCLUDED.document,
                                    metadata = EXCLUDED.metadata,
                                    embedding = EXCLUDED.embedding;
                                """,
                                (self.collection_name, cid, source, cand_id, doc, meta_json, vec_list),
                            )
        finally:
            conn.close()

    def delete(self, where: dict):
        where_sql, params = self._where_clause(where)
        conn = self._connect()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(f"DELETE FROM {self.table} WHERE {where_sql};", tuple(params))
        finally:
            conn.close()

    def query(self, vector, n: int, where: dict = None) -> list[tuple[str, float]]:
        limit_n = max(1, int(n))
        where_sql, params = self._where_clause(where)
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                if self._has_pgvector:
                    v_lit = _vec_literal(vector)
                    sql = (
                        f"SELECT id, 1.0 - (embedding <=> %s::vector) AS sim "
                        f"FROM {self.table} "
                        f"WHERE {where_sql} "
                        f"ORDER BY embedding <=> %s::vector "
                        f"LIMIT %s;"
                    )
                    cur.execute(sql, tuple([v_lit] + params + [v_lit, limit_n]))
                    rows = cur.fetchall()
                    return [(r[0], max(0.0, float(r[1]))) for r in rows]
                else:
                    import numpy as np
                    cur.execute(
                        f"SELECT id, embedding FROM {self.table} WHERE {where_sql};",
                        tuple(params),
                    )
                    q = np.asarray(vector, dtype=float)
                    q_norm = np.linalg.norm(q) or 1.0
                    scored = []
                    for rid, emb in cur.fetchall():
                        if emb is None:
                            continue
                        e = np.asarray(emb, dtype=float)
                        den = (q_norm * np.linalg.norm(e)) or 1.0
                        scored.append((rid, max(0.0, float(q @ e / den))))
                    return sorted(scored, key=lambda x: -x[1])[:limit_n]
        finally:
            conn.close()

    def get(self, ids=None, where=None, embeddings=False) -> dict:
        out = {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
        where_sql, params = self._where_clause(where)
        if ids is not None:
            id_list = list(ids)
            if not id_list:
                return out
            where_sql += " AND id = ANY(%s)"
            params.append(id_list)

        emb_Select = ", embedding::text" if (embeddings and self._has_pgvector) else (", embedding" if embeddings else "")
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT id, document, metadata{emb_Select} FROM {self.table} WHERE {where_sql} ORDER BY id;",
                    tuple(params),
                )
                for row in cur.fetchall():
                    out["ids"].append(row[0])
                    out["documents"].append(row[1])
                    meta = row[2]
                    if isinstance(meta, str):
                        meta = json.loads(meta)
                    out["metadatas"].append(meta or {})
                    if embeddings:
                        raw_emb = row[3]
                        if isinstance(raw_emb, str):
                            raw_emb = [float(x) for x in raw_emb.strip("[]").split(",") if x.strip()]
                        elif raw_emb is not None:
                            raw_emb = [float(x) for x in raw_emb]
                        else:
                            raw_emb = []
                        out["embeddings"].append(raw_emb)
            return out
        finally:
            conn.close()


@register("store", "chroma")
class ChromaStore(BaseStore):
    name = "ChromaDB (persistent HNSW)"
    _clients: dict = {}
    _clients_lock = threading.Lock()

    def __init__(self, persist_dir, embedder_id: str):
        if hasattr(persist_dir, "path"):
            persist_dir = str(persist_dir.path("chroma_dir"))
        if not CHROMA_AVAILABLE:
            raise RuntimeError("chromadb is not installed: pip install chromadb")
        with self._clients_lock:   # one client per directory per process
            client = self._clients.get(str(persist_dir))
            if client is None:
                client = chromadb.PersistentClient(path=str(persist_dir))
                self._clients[str(persist_dir)] = client
        self.collection_name = collection_name(embedder_id)
        self.col = client.get_or_create_collection(name=self.collection_name,
                                                   metadata={"hnsw:space": "cosine"})

    def count(self):
        return self.col.count()

    def upsert(self, ids, documents, metadatas, embeddings):
        step = 500
        for i in range(0, len(ids), step):
            self.col.upsert(ids=ids[i:i + step], documents=documents[i:i + step],
                            metadatas=metadatas[i:i + step], embeddings=embeddings[i:i + step])

    def delete(self, where):
        self.col.delete(where=where)

    def query(self, vector, n, where=None):
        total = self.col.count()
        if total == 0:
            return []
        kwargs = {"query_embeddings": [vector], "n_results": max(1, min(n, total)), "include": ["distances"]}
        if where:
            kwargs["where"] = where
        res = self.col.query(**kwargs)
        ids = res["ids"][0] if res.get("ids") else []
        dists = res["distances"][0] if res.get("distances") else []
        return [(i, max(0.0, 1.0 - d)) for i, d in zip(ids, dists)]

    def get(self, ids=None, where=None, embeddings=False):
        include = ["documents", "metadatas"] + (["embeddings"] if embeddings else [])
        out = {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
        if ids is not None:                                  # explicit ids: chunk the request
            for i in range(0, len(ids), 500):
                r = self.col.get(ids=ids[i:i + 500], include=include)
                self._extend(out, r, embeddings)
            return out
        offset, page = 0, 2000                               # full scan, paginated
        while True:
            kw = {"include": include, "limit": page, "offset": offset}
            if where:
                kw["where"] = where
            r = self.col.get(**kw)
            if not r["ids"]:
                break
            self._extend(out, r, embeddings)
            offset += len(r["ids"])
            if len(r["ids"]) < page:
                break
        return out

    @staticmethod
    def _extend(out, r, embeddings):
        out["ids"].extend(r["ids"])
        out["documents"].extend(r["documents"])
        out["metadatas"].extend(r["metadatas"])
        if embeddings and r.get("embeddings") is not None:
            out["embeddings"].extend([list(e) for e in r["embeddings"]])


@register("store", "memory")
class MemoryStore(BaseStore):
    """In-memory vector store (per persist_dir namespace)."""
    persistent = True
    name = "In-memory vector store"
    _spaces: dict = {}

    def __init__(self, persist_dir, embedder_id: str):
        self.collection_name = collection_name(embedder_id)
        key = (str(persist_dir), self.collection_name)
        self.rows = self._spaces.setdefault(key, {})

    def count(self):
        return len(self.rows)

    def upsert(self, ids, documents, metadatas, embeddings):
        for i, d, m, e in zip(ids, documents, metadatas, embeddings):
            self.rows[i] = (d, m, e)

    def _match(self, meta, where):
        if not where:
            return True
        for k, cond in where.items():
            v = meta.get(k)
            if isinstance(cond, dict) and "$in" in cond:
                if v not in cond["$in"]:
                    return False
            elif v != cond:
                return False
        return True

    def delete(self, where):
        for i in [i for i, (_, m, _) in self.rows.items() if self._match(m, where)]:
            del self.rows[i]

    def query(self, vector, n, where=None):
        import numpy as np
        q = np.asarray(vector, dtype=float)
        scored = []
        for i, (_, m, e) in self.rows.items():
            if self._match(m, where):
                e = np.asarray(e, dtype=float)
                den = (np.linalg.norm(q) * np.linalg.norm(e)) or 1.0
                scored.append((i, max(0.0, float(q @ e / den))))
        return sorted(scored, key=lambda x: -x[1])[:n]

    def get(self, ids=None, where=None, embeddings=False):
        out = {"ids": [], "documents": [], "metadatas": [], "embeddings": []}
        for i, (d, m, e) in self.rows.items():
            if (ids is None or i in set(ids)) and self._match(m, where):
                out["ids"].append(i); out["documents"].append(d); out["metadatas"].append(m)
                if embeddings:
                    out["embeddings"].append(list(e))
        return out


def create_store(config, embedder_id: str, kind: str = None) -> BaseStore:
    from .registry import create
    kind = (kind or config.get("retrieval.store", "pgvector")).lower()
    if kind in ("pgvector", "postgres", "postgresql"):
        return create("store", "pgvector", config, embedder_id)
    if kind == "chroma" and not CHROMA_AVAILABLE:
        kind = "memory"
    return create("store", kind, str(config.path("chroma_dir")), embedder_id)
