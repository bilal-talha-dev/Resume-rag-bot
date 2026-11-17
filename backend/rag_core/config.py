"""
Configuration for both pipelines.

Precedence (lowest -> highest):
    built-in DEFAULTS  <  rag_config.yaml  <  environment variables  <  runtime overrides

Everything a user may want to customise lives here, so no pipeline code has to change.
"""
import copy
import os
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

DEFAULT_SECTION_ALIASES = {
    "SUMMARY": ["summary", "professional summary", "profile", "about me", "about", "objective",
                "career objective", "personal statement", "executive summary"],
    "EXPERIENCE": ["experience", "work experience", "professional experience", "employment",
                   "employment history", "work history", "career history", "relevant experience",
                   "internships", "internship experience"],
    "EDUCATION": ["education", "academic background", "academic qualifications",
                  "education & training", "qualifications", "academics"],
    "SKILLS": ["skills", "technical skills", "key skills", "core competencies", "skills & tools",
               "technologies", "tech stack", "skills summary", "technical expertise"],
    "PROJECTS": ["projects", "personal projects", "academic projects", "selected projects",
                 "key projects", "notable projects"],
    "CERTIFICATIONS": ["certifications", "certificates", "licenses", "courses", "training",
                       "certifications & courses", "licenses & certifications"],
    "ACHIEVEMENTS": ["achievements", "awards", "honors", "accomplishments", "awards & honors"],
    "PUBLICATIONS": ["publications", "research", "papers"],
    "LANGUAGES": ["languages"],
    "INTERESTS": ["interests", "hobbies"],
    "VOLUNTEERING": ["volunteering", "volunteer experience", "extracurricular activities",
                     "activities", "leadership"],
    "REFERENCES": ["references"],
}

# trigger words -> extra words that usually appear in a resume for that intent (generic, editable)
DEFAULT_SYNONYMS = [
    {"when": ["live", "lives", "living", "reside", "based", "location", "located", "city", "address", "country", "hometown"],
     "add": "location city address country contact"},
    {"when": ["company", "companies", "employer", "employers", "worked", "work", "working", "job", "jobs",
              "career", "employment", "organization", "firm", "role", "roles", "position", "join", "joined"],
     "add": "experience company employer developer engineer"},
    {"when": ["current", "currently", "latest", "present", "now", "recent", "recently", "today"],
     "add": "present current"},
    {"when": ["project", "projects", "built", "build", "made", "created", "portfolio"],
     "add": "projects project built developed"},
    {"when": ["skill", "skills", "tech", "technology", "technologies", "stack", "know", "knows",
              "proficient", "expertise", "tools", "tool", "framework", "frameworks", "programming"],
     "add": "skills technologies tools languages frameworks"},
    {"when": ["experience", "years", "seniority", "senior", "junior"],
     "add": "experience years summary"},
    {"when": ["contact", "email", "mail", "phone", "number", "mobile", "reach", "linkedin", "whatsapp", "call"],
     "add": "contact email phone linkedin github"},
    {"when": ["study", "studied", "degree", "university", "college", "school", "education", "graduate",
              "graduated", "gpa", "cgpa", "grade", "academic", "qualification", "qualifications"],
     "add": "education degree university bachelor master gpa cgpa"},
    {"when": ["language", "languages", "speak", "speaks", "fluent"],
     "add": "languages fluent native"},
    {"when": ["certificate", "certificates", "certification", "certifications", "certified", "course", "courses"],
     "add": "certifications certificates courses"},
    {"when": ["cloud", "devops", "deploy", "deployment", "infra", "infrastructure"],
     "add": "cloud devops aws azure gcp docker kubernetes terraform ci/cd"},
    {"when": ["achievement", "achievements", "accomplishment", "impact", "result", "results"],
     "add": "achieved improved reduced increased delivered"},
]

DEFAULTS = {
    "paths": {
        "resumes_dir": "resumes",      # drop resumes here
        "data_dir": "data",            # manifest lives here
        "chroma_dir": "chroma_db",
    },
    "plugins": [],                     # python modules to import (they call registry.register)

    # ------------------------------------------------------------ POSTGRESQL + PGVECTOR
    "postgres": {
        "url": "",                     # e.g. postgresql://postgres:postgres@localhost:5432/rag_db (or set DATABASE_URL in .env)
        "host": "localhost",
        "port": 5432,
        "dbname": "rag_db",
        "user": "postgres",
        "password": "postgres",
        "table": "rag_chunks",
        "index_type": "hnsw",          # hnsw (vector_cosine_ops) | none
    },

    # ------------------------------------------------------------ INGESTION
    "ingestion": {
        "extensions": [".pdf", ".docx", ".txt", ".md"],
        "recursive": True,
        "max_file_mb": 15,
        "auto_ingest_on_start": True,  # background incremental ingest when the server boots
        "incremental": True,           # skip files whose content+settings did not change
        "delete_missing": True,        # remove index entries of files deleted from the folder
        "workers": 4,                  # parallel load/parse/chunk
        "parser": "resume",
        "candidate_name_source": "auto",   # auto | text | filename
        "section_aliases": DEFAULT_SECTION_ALIASES,
        "detect_unknown_headers": False,   # treat unknown ALL-CAPS short lines as section headers
        "chunker": "section",              # section | fixed
        "chunk": {
            "max_chars": 1200,
            "overlap_chars": 150,
            "min_chars": 80,
            "split_entries": ["EXPERIENCE", "PROJECTS"],  # one chunk per role / project
        },
        "embedder": "auto",            # auto | gemini | local
        "embed_batch_size": 50,        # Gemini batchEmbedContents allows up to 100
        "embedding_dims": 768,
        "fallback_to_local": True,     # if Gemini is unreachable, index with the offline embedder
    },

    # ------------------------------------------------------------ RETRIEVAL
    "retrieval": {
        "store": "pgvector",           # pgvector (PostgreSQL + pgvector) | chroma | memory
        "fetch_k": 80,                 # candidates pulled from each of vector / keyword search
        "candidate_limit": 6,          # how many resumes the LLM sees for pool-wide questions
        "max_chunks_per_candidate": 4,
        "weights": {"semantic": 0.55, "keyword": 0.45},
        "candidate_detection": True,   # "tell me about Ali Khan" -> only search Ali Khan's resume
        "profile_mode": True,          # named candidate -> send their whole resume (best accuracy)
        "context_max_chars": 16000,
        "history_turns": 6,
        "reranker": "none",            # none | custom plugin name
        "synonyms": DEFAULT_SYNONYMS,
    },

    # ------------------------------------------------------------ GENERATION
    "generation": {
        "generator": "gemini",
        "models": ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"],
        "temperature": 0.3,
        "timeout_s": 40,
        "system_prompt": None,         # None = built-in; or a string using {today} {total} {shown}
    },
    "gemini": {"embed_model": "gemini-embedding-001"},
}


def deep_merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class Config:
    def __init__(self, data: dict, base_dir: str):
        self.data = data
        self.base_dir = Path(base_dir)

    def get(self, dotted: str, default=None):
        cur = self.data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def section(self, name: str) -> dict:
        return self.data.get(name, {})

    def path(self, key: str) -> Path:
        p = Path(self.get(f"paths.{key}"))
        return p if p.is_absolute() else self.base_dir / p

    def with_overrides(self, overrides: dict) -> "Config":
        return Config(deep_merge(self.data, overrides), str(self.base_dir))

    def public_dict(self) -> dict:
        out = copy.deepcopy(self.data)
        if "postgres" in out and isinstance(out["postgres"], dict):
            if out["postgres"].get("password"):
                out["postgres"]["password"] = "***"
            if out["postgres"].get("url") and "@" in out["postgres"]["url"]:
                out["postgres"]["url"] = "***@" + out["postgres"]["url"].split("@", 1)[1]
        return out


def load_config(path: str = None, overrides: dict = None, base_dir: str = None) -> Config:
    base = Path(base_dir or Path(__file__).resolve().parent.parent)
    cfg_path = Path(path or os.getenv("RAG_CONFIG") or base / "rag_config.yaml")
    data = copy.deepcopy(DEFAULTS)
    if cfg_path.exists():
        if yaml is None:
            raise RuntimeError("rag_config.yaml found but PyYAML is not installed: pip install pyyaml")
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = deep_merge(data, yaml.safe_load(f) or {})

    # environment overrides (kept compatible with .env names)
    env = os.environ
    if env.get("GEMINI_MODELS"):
        data["generation"]["models"] = [m.strip() for m in env["GEMINI_MODELS"].split(",") if m.strip()]
    if env.get("GEMINI_EMBED_MODEL"):
        data["gemini"]["embed_model"] = env["GEMINI_EMBED_MODEL"].strip()
    if env.get("RAG_EMBEDDER"):
        data["ingestion"]["embedder"] = env["RAG_EMBEDDER"].strip().lower()
    if env.get("RAG_STORE"):
        data["retrieval"]["store"] = env["RAG_STORE"].strip().lower()
    if env.get("DATABASE_URL") or env.get("PGVECTOR_URL") or env.get("POSTGRES_URL"):
        data["postgres"]["url"] = (env.get("DATABASE_URL") or env.get("PGVECTOR_URL") or env.get("POSTGRES_URL")).strip()
    if env.get("POSTGRES_HOST"):
        data["postgres"]["host"] = env["POSTGRES_HOST"].strip()
    if env.get("POSTGRES_PORT"):
        data["postgres"]["port"] = int(env["POSTGRES_PORT"].strip())
    if env.get("POSTGRES_DB"):
        data["postgres"]["dbname"] = env["POSTGRES_DB"].strip()
    if env.get("POSTGRES_USER"):
        data["postgres"]["user"] = env["POSTGRES_USER"].strip()
    if env.get("POSTGRES_PASSWORD"):
        data["postgres"]["password"] = env["POSTGRES_PASSWORD"]
    if env.get("RAG_RESUMES_DIR"):
        data["paths"]["resumes_dir"] = env["RAG_RESUMES_DIR"].strip()
    if env.get("RAG_CHROMA_DIR"):
        data["paths"]["chroma_dir"] = env["RAG_CHROMA_DIR"].strip()
    if env.get("RAG_DATA_DIR"):
        data["paths"]["data_dir"] = env["RAG_DATA_DIR"].strip()

    if overrides:
        data = deep_merge(data, overrides)
    return Config(data, str(base))
