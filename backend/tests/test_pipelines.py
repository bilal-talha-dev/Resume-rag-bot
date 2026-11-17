"""
Comprehensive Test Suite for Resume RAG v2:
  1. PositiveUnitTests          — Loaders (PDF/DOCX/TXT/MD/tables), Parser (aliases, contact, links), Chunkers, BM25Index, Embedder, Config
  2. NegativeUnitTests          — Unsupported formats, empty/corrupt/oversize files, unknown plugins, empty store, title-as-name rejection
  3. PgVectorStoreTests         — PostgreSQL + pgvector schema, HNSW index, upsert, delete, and <=> cosine query
  4. IntegrationPipelineTests   — End-to-end Ingestion -> Store -> Retrieval (Candidate scope, Pool scope, Pronouns, Duplicate names)
  5. LifecycleIntegrationTests  — Incremental diffing, modified/deleted file sync, corrupt file isolation, config-change re-indexing
  6. GeminiWiringTests          — Batch embedding (50/call), taskType verification, HTTP 404/503 model fallback, keyword degradation
  7. ApiViewsIntegrationTests   — REST API endpoints (/api/health, /api/query, /api/upload, /api/candidates, /api/chunks, /api/config)

Run from backend/:
    python -m unittest tests.test_pipelines -v
"""
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.pop("GEMINI_API_KEY", None)

from rag_core import NothingIndexed, build, load_config, registry  # noqa: E402
from rag_core.embeddings import LocalHashEmbedder  # noqa: E402
from rag_core.ingestion import chunkers, loaders, parsers  # noqa: E402
from rag_core.retrieval.bm25 import BM25Index  # noqa: E402
from rag_core.types import LoaderError  # noqa: E402
from tests.make_sample_resumes import main as make_resumes, write_pdf  # noqa: E402

N = 45


def make_system(root, overrides=None):
    ov = {
        "paths": {"resumes_dir": f"{root}/resumes", "data_dir": f"{root}/data", "chroma_dir": f"{root}/chroma"},
        "ingestion": {"embedder": "local"},
        "retrieval": {"store": "memory"},
    }
    for k, v in (overrides or {}).items():
        ov.setdefault(k, {}).update(v)
    return build(load_config(overrides=ov), log=lambda *a: None)


# =============================================================================
# 1. POSITIVE UNIT TESTS
# =============================================================================
class PositiveUnitTests(unittest.TestCase):
    """Unit tests verifying each individual component on valid inputs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rag_unit_pos_"))
        self.cfg = load_config()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_01_normalize_text_cleans_bullets_and_whitespace(self):
        raw = "  ▪ Built APIs\n(cid:127) Scaled DB\n\x7f Led team\n   Multiple   spaces  "
        norm = loaders.normalize_text(raw)
        lines = norm.split("\n")
        self.assertEqual(lines[0], "• Built APIs")
        self.assertEqual(lines[1], "• Scaled DB")
        self.assertEqual(lines[2], "• Led team")
        self.assertEqual(lines[3], "Multiple spaces")

    def test_02_loaders_pdf_docx_table_txt_and_md(self):
        # 1. TXT & MD
        txt_file = self.tmp / "cand.txt"
        md_file = self.tmp / "cand.md"
        txt_file.write_text("Ali Khan\nSUMMARY\n• Senior Accountant", encoding="utf-8")
        md_file.write_text("Sara Ahmed\nWORK EXPERIENCE\n• HR Manager", encoding="utf-8")
        self.assertIn("Senior Accountant", loaders.load_file(str(txt_file)))
        self.assertIn("HR Manager", loaders.load_file(str(md_file)))

        # 2. DOCX with both paragraphs and a table
        import docx
        docx_file = self.tmp / "cand.docx"
        d = docx.Document()
        d.add_paragraph("Usman Sheikh")
        tbl = d.add_table(rows=1, cols=3)
        tbl.rows[0].cells[0].text = "Supply Chain Manager"
        tbl.rows[0].cells[1].text = "Master Tiles"
        tbl.rows[0].cells[2].text = "2021 - Present"
        d.save(str(docx_file))
        docx_text = loaders.load_file(str(docx_file))
        self.assertIn("Usman Sheikh", docx_text)
        self.assertIn("Supply Chain Manager | Master Tiles | 2021 - Present", docx_text)

        # 3. PDF
        pdf_file = self.tmp / "cand.pdf"
        write_pdf(pdf_file, ["Fatima Zahra", "SUMMARY", "• Talent Acquisition Lead"])
        pdf_text = loaders.load_file(str(pdf_file))
        self.assertIn("Fatima Zahra", pdf_text)
        self.assertIn("Talent Acquisition Lead", pdf_text)

    def test_03_parser_extracts_identity_and_normalizes_section_aliases(self):
        parser = parsers.ResumeParser(self.cfg)
        sample_text = "\n".join([
            "Ayesha Malik",
            "Accounts & Taxation Manager | Karachi",
            "ayesha.malik@example.com | +92 333 2190482 | linkedin.com/in/ayesha-malik | github.com/ayesham",
            "EXECUTIVE SUMMARY",
            "ACCA member with 8 years of experience in IFRS and corporate taxation.",
            "EMPLOYMENT HISTORY",
            "Accounts Manager | Unilever Pakistan | Mar 2022 - Present",
            "• Managed monthly general ledger close and FBR filings.",
            "CORE COMPETENCIES",
            "• IFRS, SAP FICO, Oracle NetSuite, Taxation",
            "ACADEMIC QUALIFICATIONS",
            "BSc Applied Accounting | Oxford Brookes University | 2014 - 2018",
            "LICENSES & CERTIFICATIONS",
            "• ACCA Fellow (FCCA)",
        ])
        parsed = parser.parse(sample_text, "R03_Ayesha_Malik_Resume.pdf")
        self.assertEqual(parsed.name, "Ayesha Malik")
        self.assertEqual(parsed.email, "ayesha.malik@example.com")
        self.assertIn("+92 333 2190482", parsed.phone)
        self.assertEqual(len(parsed.links), 2)
        self.assertEqual(parsed.headline, "Accounts & Taxation Manager | Karachi")
        sec_names = [s for s, _ in parsed.sections]
        self.assertEqual(sec_names, ["HEADER", "SUMMARY", "EXPERIENCE", "SKILLS", "EDUCATION", "CERTIFICATIONS"])

    def test_04_section_chunker_splits_jobs_and_projects_individually(self):
        parser = parsers.ResumeParser(self.cfg)
        chunker = chunkers.SectionChunker(self.cfg)
        text = "\n".join([
            "Bilal Ahmed",
            "bilal@example.com | +92 300 1112233",
            "EXPERIENCE",
            "Senior Pharmacist | AKUH | Jan 2022 – Present",
            "• Directed clinical pharmacy rounds across 65 ICU beds and reduced prescribing errors by 74%.",
            "Staff Pharmacist | Shaukat Khanum | Jan 2019 – Dec 2021",
            "• Supervised unit-dose dispensing and sterile IV admixtures for oncology wards.",
            "PROJECTS",
            "ICU Antimicrobial Stewardship | Clinical Pharmacokinetics | 2023 – 2024",
            "• Cut broad-spectrum antibiotic expenditure by 28% across inpatient units.",
        ])
        parsed = parser.parse(text, "Bilal_Ahmed.pdf")
        cks = chunker.chunk(parsed, "bilal-ahmed-0001")
        exp_chunks = [c for c in cks if c.section == "EXPERIENCE"]
        self.assertEqual(len(exp_chunks), 2)  # 2 separate job entries -> 2 separate chunks
        self.assertIn("AKUH", exp_chunks[0].entry)
        self.assertIn("Shaukat Khanum", exp_chunks[1].entry)

    def test_05_bm25_and_local_embedder_accuracy(self):
        docs = [
            "Chartered Accountant with IFRS, SAP FICO, and FBR income tax audit experience",
            "Human Resources manager specializing in Workday HCM, payroll, and labor laws",
            "Civil structural engineer skilled in Primavera P6, AutoCAD, and ETABS",
        ]
        bm = BM25Index(docs)
        scores = bm.scores(["ifrs", "sap", "fico", "tax"])
        self.assertEqual(max(scores, key=scores.get), 0)

        emb = LocalHashEmbedder(dims=768)
        v1 = emb.embed_query("IFRS SAP FICO Chartered Accountant")
        v2 = emb.embed_query("IFRS SAP FICO Chartered Accountant")
        self.assertEqual(len(v1), 768)
        self.assertEqual(v1, v2)  # deterministic

    def test_06_config_overrides_and_password_masking(self):
        cfg = load_config(overrides={"postgres": {"password": "supersecret", "url": "postgresql://u:secret@db.host:5432/rag"}})
        pub = cfg.public_dict()
        self.assertEqual(pub["postgres"]["password"], "***")
        self.assertTrue(pub["postgres"]["url"].startswith("***@"))


# =============================================================================
# 2. NEGATIVE UNIT TESTS
# =============================================================================
class NegativeUnitTests(unittest.TestCase):
    """Unit tests verifying graceful failure and error handling on invalid/corrupt inputs."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="rag_unit_neg_"))
        self.cfg = load_config()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_01_unsupported_file_extension_raises_loader_error(self):
        bad = self.tmp / "malware.exe"
        bad.write_bytes(b"MZ\x90\x00")
        with self.assertRaises(LoaderError) as cm:
            loaders.load_file(str(bad))
        self.assertIn("no loader registered", str(cm.exception))

    def test_02_empty_txt_and_empty_docx_raise_loader_error(self):
        empty_txt = self.tmp / "empty.txt"
        empty_txt.write_text("   \n\t  ", encoding="utf-8")
        with self.assertRaises(LoaderError) as cm1:
            loaders.load_file(str(empty_txt))
        self.assertIn("empty", str(cm1.exception).lower())

        import docx
        empty_docx = self.tmp / "empty.docx"
        docx.Document().save(str(empty_docx))
        with self.assertRaises(LoaderError) as cm2:
            loaders.load_file(str(empty_docx))
        self.assertIn("empty", str(cm2.exception).lower())

    def test_03_corrupt_pdf_raises_loader_error(self):
        bad_pdf = self.tmp / "corrupt.pdf"
        bad_pdf.write_bytes(b"%PDF-1.4 corrupt bytes without xref or text")
        with self.assertRaises(LoaderError):
            loaders.load_file(str(bad_pdf))

    def test_04_oversize_file_rejected_during_ingestion(self):
        ing, _ = make_system(str(self.tmp), {"ingestion": {"max_file_mb": 0.0001}})
        big_file = Path(self.tmp) / "resumes" / "huge_resume.txt"
        big_file.write_text("A" * 5000, encoding="utf-8")
        report = ing.run(verbose=False)
        self.assertEqual(report["ingested"], 0)
        self.assertEqual(report["failed"], 1)
        self.assertIn("max_file_mb", report["failures"][0]["error"])

    def test_05_query_on_empty_workspace_raises_nothing_indexed(self):
        _, ret = make_system(str(self.tmp))
        with self.assertRaises(NothingIndexed):
            ret.query("Who knows accounting?", verbose=False)

    def test_06_unknown_registry_component_raises_key_error(self):
        with self.assertRaises(KeyError) as cm:
            registry.get("chunker", "non_existent_chunker")
        self.assertIn("section", str(cm.exception))

    def test_07_parser_rejects_job_title_as_candidate_name(self):
        parser = parsers.ResumeParser(self.cfg)
        # First line is a job title ("Senior Software Engineer"), not a person's name
        text = "Senior Software Engineer\nSUMMARY\nExperienced engineer in Lahore."
        parsed = parser.parse(text, "Amina_Siddiqui_Resume_15.pdf")
        # Should fall back to filename extraction rather than picking "Senior Software Engineer"
        self.assertEqual(parsed.name, "Amina Siddiqui")


# =============================================================================
# 3. POSTGRESQL + PGVECTOR STORE INTEGRATION TESTS
# =============================================================================
class PgVectorStoreTests(unittest.TestCase):
    """Verifies PostgresVectorStore SQL schema setup (vector extension + HNSW index), upsert, delete, and <=> query."""

    def setUp(self):
        import numpy as np
        from rag_core import store as store_mod

        self.sql_log = []
        self.rows = {}

        class FakeCursor:
            def __init__(cur_self):
                cur_self._last = []

            def __enter__(cur_self):
                return cur_self

            def __exit__(cur_self, *a):
                pass

            def execute(cur_self, sql, params=None):
                s = " ".join(sql.split())
                self.sql_log.append((s, params))
                if s.startswith("INSERT INTO"):
                    col, cid, src, cand_id, doc, meta_json, vec_lit = params
                    emb = [float(x) for x in vec_lit.strip("[]").split(",")]
                    self.rows[(col, cid)] = (src, cand_id, doc, json.loads(meta_json), emb)
                elif s.startswith("SELECT COUNT(*)"):
                    col = params[0]
                    cur_self._last = [(sum(1 for (c, _) in self.rows if c == col),)]
                elif s.startswith("DELETE FROM"):
                    col = params[0]
                    if "source = %s" in s:
                        src = params[1]
                        for k in [k for k, v in self.rows.items() if k[0] == col and v[0] == src]:
                            del self.rows[k]
                elif "1.0 - (embedding <=> %s::vector)" in s:
                    v_lit = params[0]
                    col = params[1]
                    limit_n = params[-1]
                    q = np.asarray([float(x) for x in v_lit.strip("[]").split(",")], dtype=float)
                    allowed_cands = params[2] if "candidate_id = ANY(%s)" in s else None
                    scored = []
                    for (c, cid), (_src, cand_id, _doc, _meta, emb) in self.rows.items():
                        if c != col:
                            continue
                        if allowed_cands is not None and cand_id not in set(allowed_cands):
                            continue
                        e = np.asarray(emb, dtype=float)
                        den = (np.linalg.norm(q) * np.linalg.norm(e)) or 1.0
                        scored.append((cid, float(q @ e / den)))
                    scored.sort(key=lambda x: -x[1])
                    cur_self._last = scored[:limit_n]
                elif s.startswith("SELECT id, document, metadata"):
                    col = params[0]
                    id_filter = set(params[1]) if "id = ANY(%s)" in s else None
                    has_emb = "embedding::text" in s
                    res = []
                    for (c, cid), (_src, _cand_id, doc, meta, emb) in sorted(self.rows.items()):
                        if c != col or (id_filter is not None and cid not in id_filter):
                            continue
                        row = [cid, doc, meta]
                        if has_emb:
                            row.append("[" + ",".join(str(x) for x in emb) + "]")
                        res.append(tuple(row))
                    cur_self._last = res

            def fetchone(cur_self):
                return cur_self._last[0] if cur_self._last else None

            def fetchall(cur_self):
                return list(cur_self._last)

        class FakeConn:
            autocommit = False
            def __enter__(conn_self): return conn_self
            def __exit__(conn_self, *a): pass
            def cursor(conn_self): return FakeCursor()
            def close(conn_self): pass

        self._orig_connect = store_mod.PostgresVectorStore._connect
        store_mod.PostgresVectorStore._connect = lambda s: FakeConn()
        self.store_mod = store_mod
        self.root = tempfile.mkdtemp(prefix="rag_pg_")
        make_resumes(f"{self.root}/resumes", 8)

    def tearDown(self):
        self.store_mod.PostgresVectorStore._connect = self._orig_connect
        shutil.rmtree(self.root, ignore_errors=True)

    def test_pgvector_end_to_end_ingest_and_query(self):
        ing, ret = make_system(self.root, {"retrieval": {"store": "pgvector"}})
        r = ing.run(verbose=False)
        self.assertEqual(r["vector_db"], "PostgreSQL + pgvector (HNSW)")
        self.assertEqual(r["ingested"], 8)
        self.assertGreater(r["total_chunks_in_store"], 40)
        executed_sql = " ; ".join(s for s, _ in self.sql_log)
        self.assertIn("CREATE EXTENSION IF NOT EXISTS vector;", executed_sql)
        self.assertIn("USING hnsw (embedding vector_cosine_ops)", executed_sql)

        res = ret.query("Which candidates have Python or Docker experience?", verbose=False)
        self.assertEqual(res["vector_db"], "PostgreSQL + pgvector (HNSW)")
        self.assertTrue(res["candidates"])


# =============================================================================
# 4. END-TO-END PIPELINE INTEGRATION TESTS
# =============================================================================
class IntegrationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.mkdtemp(prefix="rag_test_")
        make_resumes(f"{cls.root}/resumes", N)
        cls.ing, cls.ret = make_system(cls.root)
        cls.first = cls.ing.run(verbose=False)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def test_01_all_resumes_ingested(self):
        self.assertEqual(self.first["files_found"], N)
        self.assertEqual(self.first["ingested"], N)
        self.assertEqual(self.first["failed"], 0)
        self.assertGreater(self.first["total_chunks_in_store"], N * 5)

    def test_02_names_extracted_for_every_candidate(self):
        eid = self.ing.ws.manifest.embedder_ids()[0]
        cands = self.ing.ws.candidates(eid)
        self.assertEqual(len(cands), N)
        for c in cands:
            self.assertGreaterEqual(len(c["name"].split()), 2, c)
            self.assertIn("@", c["email"], c)

    def test_03_rerun_is_incremental(self):
        r = self.ing.run(verbose=False)
        self.assertEqual((r["ingested"], r["skipped_unchanged"]), (0, N))

    def test_10_named_candidate_uses_only_that_resume(self):
        eid = self.ing.ws.manifest.embedder_ids()[0]
        target = self.ing.ws.candidates(eid)[7]
        res = self.ret.query(f"Tell me about {target['name']}", verbose=False)
        if len([c for c in self.ing.ws.candidates(eid) if c["name"] == target["name"]]) == 1:
            self.assertEqual(res["scope"], "candidate")
            self.assertEqual([c["candidate_id"] for c in res["candidates"]], [target["candidate_id"]])
        self.assertEqual(res["context_mode"], "profile")
        self.assertIn(target["email"], res["injected_prompt"])

    def test_11_follow_up_pronoun_keeps_same_candidate(self):
        eid = self.ing.ws.manifest.embedder_ids()[0]
        counts = {}
        for c in self.ing.ws.candidates(eid):
            counts[c["name"]] = counts.get(c["name"], 0) + 1
        target = next(c for c in self.ing.ws.candidates(eid) if counts[c["name"]] == 1)
        hist = [{"role": "user", "content": f"Tell me about {target['name']}"}, {"role": "assistant", "content": "..."}]
        res = self.ret.query("what is his email?", history=hist, verbose=False)
        self.assertEqual([c["candidate_id"] for c in res["candidates"]], [target["candidate_id"]])

    def test_12_pool_search_finds_the_right_people(self):
        truth = set()
        for cid, rows in self._by_candidate().items():
            if any("terraform" in r.lower() for r in rows):
                truth.add(cid)
        self.assertGreaterEqual(len(truth), 2)
        res = self.ret.query("Which candidates have Terraform experience?", options={"candidate_limit": 8}, verbose=False)
        self.assertEqual(res["scope"], "pool")
        got = [c["candidate_id"] for c in res["candidates"]]
        self.assertGreaterEqual(len(got), 2)
        precision = sum(1 for g in got if g in truth) / len(got)
        recall = len(truth & set(got)) / len(truth)
        self.assertGreaterEqual(recall, 0.99, f"recall {recall}: missed {truth - set(got)}")
        self.assertGreaterEqual(precision, 0.3, f"precision {precision}")

    def test_13_pool_context_is_spread_across_candidates(self):
        res = self.ret.query("who knows react and typescript", options={"candidate_limit": 5}, verbose=False)
        self.assertEqual(len(res["candidates"]), 5)
        self.assertTrue(all(c["chunks_used"] <= 5 for c in res["candidates"]))
        self.assertEqual(res["total_candidates"], N)

    def test_14_duplicate_names_both_returned(self):
        eid = self.ing.ws.manifest.embedder_ids()[0]
        names = {}
        for c in self.ing.ws.candidates(eid):
            names.setdefault(c["name"], []).append(c["candidate_id"])
        dups = [(n, ids) for n, ids in names.items() if len(ids) > 1]
        if not dups:
            self.skipTest("no duplicate names in sample")
        n, ids = dups[0]
        res = self.ret.query(f"summarize {n}", verbose=False)
        self.assertEqual({c["candidate_id"] for c in res["candidates"]}, set(ids))

    def test_15_explicit_candidate_filter_option(self):
        eid = self.ing.ws.manifest.embedder_ids()[0]
        cid = self.ing.ws.candidates(eid)[3]["candidate_id"]
        res = self.ret.query("what skills?", options={"candidates": [cid]}, verbose=False)
        self.assertEqual([c["candidate_id"] for c in res["candidates"]], [cid])

    def test_16_answer_without_llm_key_is_extractive_not_an_error(self):
        res = self.ret.query("who knows kubernetes?", verbose=False)
        self.assertTrue(res["answer"])
        self.assertTrue("extractive" in res["used_model"] or "gemini" in res["used_model"])

    def _by_candidate(self):
        out = {}
        data = self.ing.ws.store_for(self.ing.ws.manifest.embedder_ids()[0]).get()
        for d, m in zip(data["documents"], data["metadatas"]):
            out.setdefault(m["candidate_id"], []).append(d)
        return out


# =============================================================================
# 5. LIFECYCLE INTEGRATION TESTS
# =============================================================================
class LifecycleTests(unittest.TestCase):
    """Change / delete / corrupt / re-configure while the system is live."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="rag_life_")
        make_resumes(f"{self.root}/resumes", 12)
        self.ing, self.ret = make_system(self.root)
        self.ing.run(verbose=False)
        self.dir = Path(self.root) / "resumes"

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_modified_file_reindexed_only(self):
        f = sorted(self.dir.glob("*.txt"))[0] if list(self.dir.glob("*.txt")) else sorted(self.dir.glob("*.docx"))[0]
        if f.suffix == ".txt":
            f.write_text(f.read_text() + "\nCERTIFICATIONS\nQuantum Basket Weaving Diploma\n")
        else:
            import docx
            d = docx.Document(str(f)); d.add_paragraph("Quantum Basket Weaving Diploma"); d.save(str(f))
        r = self.ing.run(verbose=False)
        self.assertEqual((r["ingested"], r["skipped_unchanged"]), (1, 11))
        res = self.ret.query("who has a Quantum Basket Weaving Diploma?", verbose=False)
        self.assertEqual(len(res["candidates"]) and res["candidates"][0]["source"], f.name)

    def test_deleted_file_removed_from_index(self):
        f = sorted(self.dir.iterdir())[0]
        before = self.ing.ws.store_for(self.ing.ws.manifest.embedder_ids()[0]).count()
        f.unlink()
        r = self.ing.run(verbose=False)
        self.assertEqual(r["removed"], 1)
        self.assertLess(r["total_chunks_in_store"], before)
        self.assertNotIn(f.name, [c["source"] for c in self.ing.ws.candidates(r["embedder"])])

    def test_one_corrupt_file_does_not_stop_the_batch(self):
        (self.dir / "broken_resume.pdf").write_bytes(b"%PDF-1.4 this is not really a pdf")
        (self.dir / "empty.txt").write_text("")
        r = self.ing.run(verbose=False)
        self.assertEqual(r["failed"], 2)
        self.assertEqual(r["files_found"], 14)
        self.assertEqual(len(self.ing.ws.candidates(r["embedder"])), 12)
        self.assertEqual(self.ret.query("python", verbose=False)["scope"], "pool")

    def test_config_change_triggers_reindex(self):
        ing2, _ = make_system(self.root, {"ingestion": {"chunk": {"max_chars": 400}}})
        r = ing2.run(verbose=False)
        self.assertEqual(r["ingested"], 12)

    def test_force_reingest(self):
        self.assertEqual(self.ing.run(force=True, verbose=False)["ingested"], 12)

    def test_new_files_picked_up(self):
        make_resumes(f"{self.root}/more", 5, seed=99)
        for f in Path(f"{self.root}/more").iterdir():
            shutil.copy(f, self.dir / ("new_" + f.name))
        r = self.ing.run(verbose=False)
        self.assertEqual((r["ingested"], r["skipped_unchanged"]), (5, 12))
        self.assertEqual(len(self.ing.ws.candidates(r["embedder"])), 17)

    def test_unreachable_gemini_falls_back_to_local(self):
        ing, ret = make_system(self.root + "_g", {"ingestion": {"embedder": "gemini"}, "paths": {"resumes_dir": f"{self.root}/resumes"}})
        r = ing.run(api_key="not-a-real-key", verbose=False)
        self.assertTrue(r["warnings"])
        self.assertTrue(r["embedder"].startswith("local"))
        self.assertEqual(r["ingested"], 12)
        shutil.rmtree(self.root + "_g", ignore_errors=True)


# =============================================================================
# 6. GEMINI API WIRING & FALLBACK INTEGRATION TESTS
# =============================================================================
class GeminiWiringTests(unittest.TestCase):
    """Gemini HTTP layer stubbed: verifies batching, task types, collections and the model fallback chain."""

    def setUp(self):
        import urllib.error
        from rag_core import embeddings as emb_mod
        from rag_core.retrieval import generator as gen_mod
        self.calls = []
        local = LocalHashEmbedder(dims=768)

        def fake_post(model, action, payload, api_key, timeout=30):
            self.calls.append((model, action, payload))
            if action == "batchEmbedContents":
                return {"embeddings": [{"values": local._embed(r["content"]["parts"][0]["text"])} for r in payload["requests"]]}
            if action == "embedContent":
                return {"embedding": {"values": local._embed(payload["content"]["parts"][0]["text"])}}
            if action == "generateContent":
                if model == "gemini-dead":
                    raise urllib.error.HTTPError("u", 404, "nf", {}, None)
                return {"candidates": [{"content": {"parts": [{"text": "STUBBED ANSWER"}]}}]}
        self._orig = (emb_mod.gemini_post, gen_mod.gemini_post)
        emb_mod.gemini_post = fake_post
        gen_mod.gemini_post = fake_post
        self.emb_mod, self.gen_mod = emb_mod, gen_mod
        self.root = tempfile.mkdtemp(prefix="rag_gem_")
        make_resumes(f"{self.root}/resumes", 30)

    def tearDown(self):
        self.emb_mod.gemini_post, self.gen_mod.gemini_post = self._orig
        shutil.rmtree(self.root, ignore_errors=True)

    def test_batching_task_types_and_collection(self):
        ing, ret = make_system(self.root, {"ingestion": {"embedder": "gemini", "embed_batch_size": 50},
                                           "generation": {"models": ["gemini-dead", "gemini-ok"]}})
        r = ing.run(api_key="k", verbose=False)
        self.assertEqual(r["embedder"], "gemini-gemini-embedding-001-768")
        self.assertEqual(r["collection"], "resumes_gemini-gemini-embedding-001-768")
        batches = [c for c in self.calls if c[1] == "batchEmbedContents"]
        self.assertEqual(len(batches), -(-r["chunks_added"] // 50))
        reqs = batches[0][2]["requests"]
        self.assertEqual({x["taskType"] for x in reqs}, {"RETRIEVAL_DOCUMENT"})
        self.assertEqual({x["outputDimensionality"] for x in reqs}, {768})

        self.calls.clear()
        res = ret.query("who knows kubernetes?", api_key="k", verbose=False)
        self.assertEqual(res["embedding_model"], "gemini-gemini-embedding-001-768")
        q = [c for c in self.calls if c[1] == "embedContent"]
        self.assertEqual(q[0][2]["taskType"], "RETRIEVAL_QUERY")
        self.assertEqual(res["answer"], "STUBBED ANSWER")
        self.assertEqual(res["used_model"], "gemini-ok")
        self.assertEqual([a["status"] for a in res["model_attempts"]], ["HTTP 404", "SUCCESS"])
        self.assertIn("### CANDIDATE:", res["injected_prompt"])

    def test_query_embedding_failure_degrades_to_keyword_search(self):
        from rag_core.types import EmbeddingUnavailable
        ing, ret = make_system(self.root, {"ingestion": {"embedder": "gemini"}})
        ing.run(api_key="k", verbose=False)
        orig = self.emb_mod.gemini_post

        def boom(model, action, payload, key, timeout=30):
            if action == "embedContent":
                raise EmbeddingUnavailable("quota")
            return orig(model, action, payload, key, timeout)
        self.emb_mod.gemini_post = boom
        res = ret.query("kubernetes terraform", api_key="k", verbose=False)
        self.assertEqual(res["embedding_model"], "keyword-only")
        self.assertTrue(res["candidates"])


# =============================================================================
# 7. DJANGO REST API VIEWS INTEGRATION TESTS (Positive & Negative HTTP Cases)
# =============================================================================
class ApiViewsIntegrationTests(unittest.TestCase):
    """Tests /api/health, /api/config, /api/candidates, /api/chunks, /api/query, /api/upload, and DELETE /api/candidates/<source>."""

    @classmethod
    def setUpClass(cls):
        cls._install_django_shim_if_needed()
        cls.root = tempfile.mkdtemp(prefix="rag_api_")
        make_resumes(f"{cls.root}/resumes", 6)
        cls.cfg = load_config(overrides={
            "paths": {"resumes_dir": f"{cls.root}/resumes", "data_dir": f"{cls.root}/data", "chroma_dir": f"{cls.root}/chroma"},
            "ingestion": {"embedder": "local"},
            "retrieval": {"store": "memory"},
        })
        cls.ing, cls.ret = build(cls.cfg, log=lambda *a: None)
        cls.ing.run(verbose=False)

        from rag_app import services, views
        services._state = {"config": cls.cfg, "ingestion": cls.ing, "retrieval": cls.ret}
        cls.views = views

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    @staticmethod
    def _install_django_shim_if_needed():
        try:
            import django
            from django.conf import settings
            if not settings.configured:
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rag_project.settings")
                django.setup()
        except ImportError:
            # Lightweight shim for environments without Django installed
            dj = types.ModuleType("django")
            conf = types.ModuleType("django.conf")
            conf.settings = types.SimpleNamespace(FRONTEND_DIST_DIR=Path("/tmp"))
            http = types.ModuleType("django.http")

            class HttpResponse(dict):
                def __init__(self, content=b"", status=200, content_type="text/html"):
                    super().__init__()
                    self.content = content.encode("utf-8") if isinstance(content, str) else content
                    self.status_code = status

            class JsonResponse(HttpResponse):
                def __init__(self, data, status=200):
                    super().__init__(json.dumps(data).encode("utf-8"), status=status, content_type="application/json")

            http.HttpResponse = HttpResponse
            http.JsonResponse = JsonResponse
            http.FileResponse = HttpResponse
            views_mod = types.ModuleType("django.views")
            dec_mod = types.ModuleType("django.views.decorators")
            csrf_mod = types.ModuleType("django.views.decorators.csrf")
            csrf_mod.csrf_exempt = lambda fn: fn
            sys.modules.update({
                "django": dj, "django.conf": conf, "django.http": http,
                "django.views": views_mod, "django.views.decorators": dec_mod,
                "django.views.decorators.csrf": csrf_mod,
            })

    def _req(self, method="GET", body=None, get_params=None, post_params=None, files=None, headers=None):
        class FakeFiles(dict):
            def getlist(self, k):
                return self.get(k, [])

        return types.SimpleNamespace(
            method=method,
            body=json.dumps(body).encode("utf-8") if body is not None else b"",
            GET=get_params or {},
            POST=post_params or {},
            FILES=FakeFiles(files or {}),
            headers=headers or {},
        )

    def test_01_health_and_config_endpoints_positive(self):
        r_health = self.views.health_view(self._req("GET"))
        self.assertEqual(r_health.status_code, 200)
        d_health = json.loads(r_health.content)
        self.assertEqual(d_health["status"], "ok")
        self.assertEqual(d_health["candidates_indexed"], 6)

        r_cfg = self.views.config_view(self._req("GET"))
        self.assertEqual(r_cfg.status_code, 200)
        d_cfg = json.loads(r_cfg.content)
        self.assertIn("ingestion", d_cfg)
        self.assertIn("retrieval", d_cfg)

    def test_02_candidates_and_chunks_endpoints_positive(self):
        r_cands = self.views.candidates_view(self._req("GET"))
        self.assertEqual(r_cands.status_code, 200)
        d_cands = json.loads(r_cands.content)
        self.assertEqual(d_cands["total"], 6)

        r_chunks = self.views.chunks_view(self._req("GET", get_params={"limit": "20"}))
        self.assertEqual(r_chunks.status_code, 200)
        d_chunks = json.loads(r_chunks.content)
        self.assertLessEqual(d_chunks["returned"], 20)
        self.assertGreater(d_chunks["total_chunks"], 20)

    def test_03_query_endpoint_positive_and_negative(self):
        # Positive: valid POST query
        r_ok = self.views.query_view(self._req("POST", body={"query": "Who knows Python or React?", "candidate_limit": 3}))
        self.assertEqual(r_ok.status_code, 200)
        d_ok = json.loads(r_ok.content)
        self.assertTrue(d_ok["answer"])
        self.assertLessEqual(len(d_ok["candidates"]), 3)

        # Negative 1: empty query -> HTTP 400
        r_bad = self.views.query_view(self._req("POST", body={"query": "   "}))
        self.assertEqual(r_bad.status_code, 400)

        # Negative 2: wrong HTTP method (GET instead of POST) -> HTTP 405
        r_method = self.views.query_view(self._req("GET"))
        self.assertEqual(r_method.status_code, 405)

    def test_04_upload_and_delete_candidate_positive_and_negative(self):
        class FakeUpload:
            def __init__(self, name, content):
                self.name = name
                self._bytes = content.encode("utf-8") if isinstance(content, str) else content
                self.size = len(self._bytes)
            def chunks(self):
                yield self._bytes

        # Negative upload: unsupported .exe file -> HTTP 400
        r_neg = self.views.upload_view(self._req("POST", post_params={"ingest": "false"}, files={"files": [FakeUpload("virus.exe", "bad")]}))
        self.assertEqual(r_neg.status_code, 400)
        self.assertEqual(json.loads(r_neg.content)["rejected"][0]["reason"], "unsupported file type")

        # Positive upload: valid .txt resume -> HTTP 201
        resume_txt = "Zainab Test\nzainab@example.com | +92 300 1234567\nSUMMARY\nChartered Accountant with IFRS."
        r_pos = self.views.upload_view(self._req("POST", post_params={"ingest": "false"}, files={"files": [FakeUpload("Zainab_Test.txt", resume_txt)]}))
        self.assertEqual(r_pos.status_code, 201)
        self.assertIn("Zainab_Test.txt", json.loads(r_pos.content)["saved"])

        # Negative delete: non-existent file -> HTTP 404
        r_del_404 = self.views.candidate_detail_view(self._req("DELETE"), "does_not_exist.pdf")
        self.assertEqual(r_del_404.status_code, 404)

        # Positive delete: existing uploaded file -> HTTP 200
        r_del_ok = self.views.candidate_detail_view(self._req("DELETE"), "Zainab_Test.txt")
        self.assertEqual(r_del_ok.status_code, 200)


class CustomisationTests(unittest.TestCase):
    def test_plugin_chunker_and_reranker_via_config(self):
        from rag_core.ingestion.chunkers import BaseChunker, _make

        @registry.register("chunker", "one_chunk")
        class OneChunk(BaseChunker):
            def chunk(self, parsed, cid):
                return [_make(parsed, cid, "ALL", "", [l for l in parsed.raw_text.split("\n")], 0)]

        calls = []

        @registry.register("reranker", "spy")
        class Spy:
            def __init__(self, config): ...
            def rerank(self, q, ranked):
                calls.append(len(ranked)); return ranked

        root = tempfile.mkdtemp(prefix="rag_custom_")
        try:
            make_resumes(f"{root}/resumes", 6)
            ing, ret = make_system(root, {"ingestion": {"chunker": "one_chunk"}, "retrieval": {"reranker": "spy"}})
            r = ing.run(verbose=False)
            self.assertEqual(r["total_chunks_in_store"], 6)
            ret.query("python developer", verbose=False)
            self.assertTrue(calls)
        finally:
            shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
