# Resume RAG — Ingestion & Retrieval pipelines (React + Django + PostgreSQL `pgvector` + Gemini)

Two independent, configurable pipelines over a shared **PostgreSQL + `pgvector`** vector store (with optional ChromaDB / in-memory modes). Drop **any number of resumes** (1, 40, 50, 500…) into `backend/resumes/` and ask questions across all of them.

```
                        ┌──────────────── PIPELINE 1: INGESTION ────────────────┐
 backend/resumes/  ───► │ discover → diff → load → parse → chunk → embed → store │──┐
 (PDF/DOCX/TXT/MD)      │  (hash)   (new/changed/deleted)   (parallel)  (batched)│  │  PostgreSQL + pgvector
                        └────────────────────────────────────────────────────────┘  │  (HNSW cosine index)
                        ┌──────────────── PIPELINE 2: RETRIEVAL ────────────────┐  │  + manifest
 question + history ──► │ understand → hybrid search → group by candidate →      │◄─┘
                        │ build context → generate (Gemini / extractive)         │───► answer
                        └────────────────────────────────────────────────────────┘
```

## Quick start (PostgreSQL + `pgvector`)

### Option A — 1-Command Docker PostgreSQL + `pgvector`
```bash
docker compose up -d            # starts pgvector/pgvector:pg16 on localhost:5432 (db: rag_db, user/pass: postgres)
```

### Option B — Existing Local PostgreSQL Server
1. Create the database (in `psql` or pgAdmin):
   ```sql
   CREATE DATABASE rag_db;
   \c rag_db
   CREATE EXTENSION IF NOT EXISTS vector;
   ```
2. Set your connection details in `backend/.env` or `backend/rag_config.yaml` (`postgres:` section):
   ```env
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/rag_db
   ```
   *(Note: When the server starts, `PostgresVectorStore` automatically runs `CREATE EXTENSION IF NOT EXISTS vector;`, creates the `rag_chunks` table, and builds the HNSW cosine index `USING hnsw (embedding vector_cosine_ops)`.)*

### Run the Backend & UI
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env            # set GEMINI_API_KEY and DATABASE_URL
python manage.py runserver      # boots, ingests resumes into PostgreSQL + pgvector, serves UI on :8000
```

No Django needed for scripting: `python cli_rag.py ingest`, `python cli_rag.py ask "Who works in HR or Accounting?"`,
`python cli_rag.py chat`, `python cli_rag.py candidates`.

## Pipeline 1 — Ingestion (`rag_core/ingestion/`)

| Stage | What it does | Customise via `rag_config.yaml` |
|---|---|---|
| discover | scans `resumes_dir`, SHA-256 per file | `extensions`, `recursive`, `max_file_mb` |
| diff | new / changed / unchanged / deleted vs. the manifest | `incremental`, `delete_missing` |
| load | PDF (pdfplumber → pypdf), DOCX (paragraphs + tables), TXT/MD | register a `loader` |
| parse | candidate name / email / phone / links + sections (alias-based headings) | `section_aliases`, `candidate_name_source`, register a `parser` |
| chunk | one chunk per section, **one per job / project**, oversize windows with overlap | `chunker: section \| fixed`, `chunk.*`, register a `chunker` |
| embed | Gemini `batchEmbedContents` (50 chunks per call), offline fallback | `embedder: auto \| gemini \| local`, register an `embedder` |
| store | upserts into PostgreSQL `rag_chunks` (`vector(768)` + HNSW index), updates manifest | `store: pgvector \| chroma \| memory`, `postgres.*` |

## Pipeline 2 — Retrieval (`rag_core/retrieval/`)

* **Candidate scope** — "Tell me about Ali Khan" / "what's *his* email?" → only that resume is searched and the
  **whole resume** is sent to the LLM. Duplicate names return every match.
* **Pool scope** — "Who has IFRS and SAP FICO?" → hybrid search (`pgvector` `<=>` cosine distance + BM25 + synonym expansion) over every chunk, then **grouped by candidate** so one resume can't crowd out the rest; the top `candidate_limit` resumes are sent, each with its best chunks and contact header.

## Tests

```bash
cd backend && python -m unittest tests.test_pipelines -v
```
