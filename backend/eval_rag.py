"""
RAG Evaluation Suite (50 Golden Questions Benchmark)
====================================================
Evaluates both Ingestion & Retrieval pipelines across 50 golden test cases spanning 5 categories:
  1. Single-Candidate Profile Queries (15 cases)
  2. Cross-Department Pool Queries — HR, Accounting, Banking, Supply Chain, Healthcare, Engineering (15 cases)
  3. Needle-in-a-Haystack Precision Queries across PDF, DOCX, TXT, and MD (10 cases)
  4. Multi-Turn Pronoun Follow-Ups & Duplicate-Name Disambiguation (5 cases)
  5. Negative / Guardrail & Edge-Case Queries (5 cases)

Metrics computed:
  * Context Recall@K (Retrieval Hit Rate %)
  * Mean Reciprocal Rank (MRR)
  * Scope Detection Accuracy (%)
  * Answer Fact Groundedness (%)
  * Overall RAG Eval Score (%)

Usage (from backend/):
  python eval_rag.py                          # fast offline eval over backend/resumes/ (saves eval_report.md & .json)
  python eval_rag.py --store memory           # run in-memory without touching PostgreSQL/Chroma
  python eval_rag.py --use-gemini             # also call live Gemini LLM for answer generation
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rag_core import build, load_config  # noqa: E402

# =============================================================================
# 50 GOLDEN EVALUATION TEST CASES
# =============================================================================
GOLDEN_DATASET = [
    # ---------------- CATEGORY 1: Candidate Profile Lookups (15 cases)
    {
        "id": "G01", "category": "1. Candidate Profile",
        "question": "Tell me about Ayesha Malik and her current role.",
        "expected_scope": "candidate",
        "expected_candidates": ["Ayesha Malik"],
        "expected_facts": ["Unilever", "ACCA", "Accounts"],
    },
    {
        "id": "G02", "category": "1. Candidate Profile",
        "question": "What is Usman Sheikh's background in Gujranwala?",
        "expected_scope": "candidate",
        "expected_candidates": ["Usman Sheikh"],
        "expected_facts": ["Supply Chain", "Master Tiles", "Gujranwala"],
    },
    {
        "id": "G03", "category": "1. Candidate Profile",
        "question": "Summarize Fatima Zahra's HR experience and certifications.",
        "expected_scope": "candidate",
        "expected_candidates": ["Fatima Zahra"],
        "expected_facts": ["Talent Acquisition", "Systems Limited", "PHRri"],
    },
    {
        "id": "G04", "category": "1. Candidate Profile",
        "question": "What does Hamza Raza do in digital marketing?",
        "expected_scope": "candidate",
        "expected_candidates": ["Hamza Raza"],
        "expected_facts": ["Digital Marketing", "Daraz", "Google Ads"],
    },
    {
        "id": "G05", "category": "1. Candidate Profile",
        "question": "Tell me about Zainab Hussain's banking and credit risk career.",
        "expected_scope": "candidate",
        "expected_candidates": ["Zainab Hussain"],
        "expected_facts": ["Credit Risk", "Habib Bank", "CFA"],
    },
    {
        "id": "G06", "category": "1. Candidate Profile",
        "question": "What is Bilal Ahmed's clinical pharmacy experience?",
        "expected_scope": "candidate",
        "expected_candidates": ["Bilal Ahmed"],
        "expected_facts": ["Clinical Pharmacist", "Aga Khan", "Pharm-D"],
    },
    {
        "id": "G07", "category": "1. Candidate Profile",
        "question": "Give me an overview of Sana Qureshi's sales experience.",
        "expected_scope": "candidate",
        "expected_candidates": ["Sana Qureshi"],
        "expected_facts": ["Regional Sales", "Coca-Cola", "Salesforce"],
    },
    {
        "id": "G08", "category": "1. Candidate Profile",
        "question": "What civil engineering projects has Omar Farooq worked on?",
        "expected_scope": "candidate",
        "expected_candidates": ["Omar Farooq"],
        "expected_facts": ["Civil", "NESPAK", "Primavera P6"],
    },
    {
        "id": "G09", "category": "1. Candidate Profile",
        "question": "What is Hira Tariq's legal and compliance background?",
        "expected_scope": "candidate",
        "expected_candidates": ["Hira Tariq"],
        "expected_facts": ["Legal Counsel", "Haidermota", "LLB"],
    },
    {
        "id": "G10", "category": "1. Candidate Profile",
        "question": "Tell me about Hassan Iqbal's mechanical plant engineering experience.",
        "expected_scope": "candidate",
        "expected_candidates": ["Hassan Iqbal"],
        "expected_facts": ["Mechanical", "Fatima Fertilizer", "SAP PM"],
    },
    {
        "id": "G11", "category": "1. Candidate Profile",
        "question": "What is Saad Chaudhry's academic and teaching background?",
        "expected_scope": "candidate",
        "expected_candidates": ["Saad Chaudhry"],
        "expected_facts": ["Lecturer", "Curriculum", "CELTA"],
    },
    {
        "id": "G12", "category": "1. Candidate Profile",
        "question": "Summarize Mariam Ansari's hospital operations experience.",
        "expected_scope": "candidate",
        "expected_candidates": ["Mariam Ansari"],
        "expected_facts": ["Hospital Operations", "Shifa International", "CPHQ"],
    },
    {
        "id": "G13", "category": "1. Candidate Profile",
        "question": "What hotel operations experience does Sofia Garcia have?",
        "expected_scope": "candidate",
        "expected_candidates": ["Sofia Garcia"],
        "expected_facts": ["Hotel Operations", "Marriott", "Opera PMS"],
    },
    {
        "id": "G14", "category": "1. Candidate Profile",
        "question": "Tell me about Arjun Verma's internal audit and forensic accounting work.",
        "expected_scope": "candidate",
        "expected_candidates": ["Arjun Verma"],
        "expected_facts": ["Internal Audit", "Fraud Examiner", "COSO"],
    },
    {
        "id": "G15", "category": "1. Candidate Profile",
        "question": "What is Adeel Warraich's banking role in Gujranwala?",
        "expected_scope": "candidate",
        "expected_candidates": ["Adeel Warraich"],
        "expected_facts": ["Bank Alfalah", "SME", "Gujranwala"],
    },

    # ---------------- CATEGORY 2: Cross-Department Pool Queries (15 cases)
    {
        "id": "G16", "category": "2. Department Pool Search",
        "question": "Which candidates are Chartered Accountants (ACA or ACCA) with IFRS and SAP FICO experience?",
        "expected_scope": "pool",
        "expected_candidates": ["Ali Khan", "Ayesha Malik", "Arjun Verma"],
        "expected_facts": ["IFRS", "ACA", "ACCA"],
    },
    {
        "id": "G17", "category": "2. Department Pool Search",
        "question": "Who has Human Resources (HR) experience with Workday, BambooHR, payroll, or talent acquisition?",
        "expected_scope": "pool",
        "expected_candidates": ["Ali Khan", "Fatima Zahra", "Michael Patel"],
        "expected_facts": ["Workday", "Talent Acquisition", "Payroll"],
    },
    {
        "id": "G18", "category": "2. Department Pool Search",
        "question": "Find supply chain and procurement managers with SAP MM, S&OP demand planning, or customs LC experience.",
        "expected_scope": "pool",
        "expected_candidates": ["Usman Sheikh", "Daniel Kim", "Shahzaib Abbasi"],
        "expected_facts": ["SAP", "Supply Chain", "Procurement"],
    },
    {
        "id": "G19", "category": "2. Department Pool Search",
        "question": "Which candidates work in banking, credit risk, Basel III, or corporate treasury FX?",
        "expected_scope": "pool",
        "expected_candidates": ["Zainab Hussain", "Nida Hashmi", "Adeel Warraich"],
        "expected_facts": ["Basel III", "Credit Risk", "Treasury"],
    },
    {
        "id": "G20", "category": "2. Department Pool Search",
        "question": "Who has clinical pharmacy, hospital operations, Pharm-D, or JCI accreditation experience?",
        "expected_scope": "pool",
        "expected_candidates": ["Bilal Ahmed", "Mariam Ansari", "Rabia Nawaz"],
        "expected_facts": ["JCI", "Pharm-D", "Hospital"],
    },
    {
        "id": "G21", "category": "2. Department Pool Search",
        "question": "Which candidates are PEC registered engineers in civil, mechanical, or electrical power engineering?",
        "expected_scope": "pool",
        "expected_candidates": ["Omar Farooq", "Hassan Iqbal", "Lucas Weber"],
        "expected_facts": ["PEC", "Primavera", "ETAP"],
    },
    {
        "id": "G22", "category": "2. Department Pool Search",
        "question": "Find digital marketing, SEO, Google Ads, or corporate PR communications specialists.",
        "expected_scope": "pool",
        "expected_candidates": ["Hamza Raza", "Priya Nair", "Khadija Baig"],
        "expected_facts": ["Google Ads", "SEO", "Communications"],
    },
    {
        "id": "G23", "category": "2. Department Pool Search",
        "question": "Who has experience in FMCG sales, retail operations, or international export merchandising?",
        "expected_scope": "pool",
        "expected_candidates": ["Sana Qureshi", "Zohaib Butt", "Carlos Mendoza"],
        "expected_facts": ["Sales", "Retail", "Export"],
    },
    {
        "id": "G24", "category": "2. Department Pool Search",
        "question": "Which candidates specialize in cybersecurity, SIEM, QRadar, CISSP, or ISO 27001?",
        "expected_scope": "pool",
        "expected_candidates": ["Fahad Lodhi"],
        "expected_facts": ["CISSP", "ISO 27001", "QRadar"],
    },
    {
        "id": "G25", "category": "2. Department Pool Search",
        "question": "Who has cloud DevOps experience with Terraform, Kubernetes, Docker, and AWS?",
        "expected_scope": "pool",
        "expected_candidates": ["Amina Siddiqui", "Muhammad Bilal Talha"],
        "expected_facts": ["Terraform", "Kubernetes", "AWS"],
    },
    {
        "id": "G26", "category": "2. Department Pool Search",
        "question": "Which candidates are based in Gujranwala across any industry?",
        "expected_scope": "pool",
        "expected_candidates": ["Usman Sheikh", "Tariq Mehmood", "Kamran Akram", "Adeel Warraich"],
        "expected_facts": ["Gujranwala"],
    },
    {
        "id": "G27", "category": "2. Department Pool Search",
        "question": "Who has QA test automation experience with Playwright, Cypress, Selenium, and JMeter?",
        "expected_scope": "pool",
        "expected_candidates": ["Haris Munir"],
        "expected_facts": ["Playwright", "JMeter", "ISTQB"],
    },
    {
        "id": "G28", "category": "2. Department Pool Search",
        "question": "Which candidates have experience in corporate law, SECP compliance, or M&A legal due diligence?",
        "expected_scope": "pool",
        "expected_candidates": ["Hira Tariq"],
        "expected_facts": ["LLB", "SECP", "Advocate High Court"],
    },
    {
        "id": "G29", "category": "2. Department Pool Search",
        "question": "Who has experience in food safety, FSSC 22000, HACCP, and Halal standards?",
        "expected_scope": "pool",
        "expected_candidates": ["Bushra Riaz"],
        "expected_facts": ["FSSC 22000", "HACCP", "Food Safety"],
    },
    {
        "id": "G30", "category": "2. Department Pool Search",
        "question": "Which candidates have clinical psychology, CBT therapy, or corporate employee wellness experience?",
        "expected_scope": "pool",
        "expected_candidates": ["Anam Bukhari"],
        "expected_facts": ["Clinical Psychologist", "CBT", "Employee Assistance"],
    },

    # ---------------- CATEGORY 3: Needle-in-a-Haystack Precision Queries (10 cases)
    {
        "id": "G31", "category": "3. Needle-in-a-Haystack",
        "question": "Which candidate negotiated Collective Bargaining (CBA) union settlements for 4,200 textile factory workers?",
        "expected_scope": "pool",
        "expected_candidates": ["Areeba Kazmi"],
        "expected_facts": ["Areeba Kazmi", "4,200", "Interloop"],
    },
    {
        "id": "G32", "category": "3. Needle-in-a-Haystack",
        "question": "Who led the Rs. 8.5B Pharmaceutical IPO on the Pakistan Stock Exchange?",
        "expected_scope": "pool",
        "expected_candidates": ["Zara Sherazi"],
        "expected_facts": ["Zara Sherazi", "8.5B", "IPO"],
    },
    {
        "id": "G33", "category": "3. Needle-in-a-Haystack",
        "question": "Who implemented the IFRS 17 Contractual Service Margin actuarial engine using Prophet software?",
        "expected_scope": "pool",
        "expected_candidates": ["Yumna Waheed"],
        "expected_facts": ["Yumna Waheed", "IFRS 17", "Prophet"],
    },
    {
        "id": "G34", "category": "3. Needle-in-a-Haystack",
        "question": "Who is JLPT N2 certified in Japanese and works in FP&A with Anaplan?",
        "expected_scope": "pool",
        "expected_candidates": ["Emily Chen"],
        "expected_facts": ["Emily Chen", "JLPT N2", "Anaplan"],
    },
    {
        "id": "G35", "category": "3. Needle-in-a-Haystack",
        "question": "Which candidate won 1st Place at the NASA Space Apps Challenge for flood-prediction satellite AI?",
        "expected_scope": "pool",
        "expected_candidates": ["Noor ul Ain"],
        "expected_facts": ["Noor ul Ain", "NASA Space Apps"],
    },
    {
        "id": "G36", "category": "3. Needle-in-a-Haystack",
        "question": "Who deployed predictive thermal IoT kiln sensors across 85 ceramics and metal factories in Gujranwala?",
        "expected_scope": "pool",
        "expected_candidates": ["Kamran Akram"],
        "expected_facts": ["Kamran Akram", "85", "Gujranwala"],
    },
    {
        "id": "G37", "category": "3. Needle-in-a-Haystack",
        "question": "Who holds a NEBOSH International Diploma and achieved 10 million safe man-hours without LTI?",
        "expected_scope": "pool",
        "expected_candidates": ["Samina Pervez"],
        "expected_facts": ["Samina Pervez", "NEBOSH", "10 Million"],
    },
    {
        "id": "G38", "category": "3. Needle-in-a-Haystack",
        "question": "Who re-engineered SKU-level Bill of Materials (BOM) costing across 320 electrical appliance SKUs in Gujranwala?",
        "expected_scope": "pool",
        "expected_candidates": ["Tariq Mehmood"],
        "expected_facts": ["Tariq Mehmood", "320", "Super Asia"],
    },
    {
        "id": "G39", "category": "3. Needle-in-a-Haystack",
        "question": "Which architect designed a 320,000 sq. ft. LEED Gold Corporate Headquarters using Revit BIM?",
        "expected_scope": "pool",
        "expected_candidates": ["Mei Lin"],
        "expected_facts": ["Mei Lin", "LEED Gold", "Revit"],
    },
    {
        "id": "G40", "category": "3. Needle-in-a-Haystack",
        "question": "Who launched the cross-border TIR regional transit freight corridor to Central Asia?",
        "expected_scope": "pool",
        "expected_candidates": ["Taimoor Sultan"],
        "expected_facts": ["Taimoor Sultan", "TIR", "Central Asia"],
    },

    # ---------------- CATEGORY 4: Multi-Turn Pronoun & Duplicate-Name Evals (5 cases)
    {
        "id": "G41", "category": "4. Multi-Turn & Duplicate Names",
        "question": "Tell me about Ali Khan",
        "expected_scope": "candidate",
        "expected_candidates": ["Ali Khan"],
        "min_same_name_matches": 2,
        "expected_facts": ["Chartered Accountant", "Human Resources"],
    },
    {
        "id": "G42", "category": "4. Multi-Turn & Duplicate Names",
        "history": [
            {"role": "user", "content": "Tell me about Usman Sheikh"},
            {"role": "assistant", "content": "Usman Sheikh is a Supply Chain Manager in Gujranwala."},
        ],
        "question": "What is his email and phone number?",
        "expected_scope": "candidate",
        "expected_candidates": ["Usman Sheikh"],
        "expected_facts": ["usman.sheikh4@example.com", "+92 301 6459821"],
    },
    {
        "id": "G43", "category": "4. Multi-Turn & Duplicate Names",
        "history": [
            {"role": "user", "content": "Tell me about Hira Tariq"},
            {"role": "assistant", "content": "Hira Tariq is a Corporate Legal Counsel in Lahore."},
        ],
        "question": "Where did she complete her law degree?",
        "expected_scope": "candidate",
        "expected_candidates": ["Hira Tariq"],
        "expected_facts": ["University of London", "LLB"],
    },
    {
        "id": "G44", "category": "4. Multi-Turn & Duplicate Names",
        "history": [
            {"role": "user", "content": "Tell me about Rizwan Satti"},
            {"role": "assistant", "content": "Rizwan Satti is a Group Product Manager at SadaPay."},
        ],
        "question": "What payment projects did he launch?",
        "expected_scope": "candidate",
        "expected_candidates": ["Rizwan Satti"],
        "expected_facts": ["Raast", "QR", "NADRA"],
    },
    {
        "id": "G45", "category": "4. Multi-Turn & Duplicate Names",
        "history": [
            {"role": "user", "content": "Tell me about Maham Gillani"},
            {"role": "assistant", "content": "Maham Gillani is a Program Manager at UNDP."},
        ],
        "question": "What donor grants has she managed?",
        "expected_scope": "candidate",
        "expected_candidates": ["Maham Gillani"],
        "expected_facts": ["UNDP", "FCDO", "USAID"],
    },

    # ---------------- CATEGORY 5: Negative / Guardrail & Edge-Case Evals (5 cases)
    {
        "id": "G46", "category": "5. Negative & Guardrails",
        "question": "Hello!",
        "expected_scope": "pool",
        "expected_candidates": [],
        "expected_facts": ["resume", "database"],
        "is_guardrail": True,
    },
    {
        "id": "G47", "category": "5. Negative & Guardrails",
        "question": "What is Ayesha Malik's blood type and passport number?",
        "expected_scope": "candidate",
        "expected_candidates": ["Ayesha Malik"],
        "forbidden_facts": ["AB+", "O+", "Passport: PK"],
        "is_guardrail": True,
    },
    {
        "id": "G48", "category": "5. Negative & Guardrails",
        "question": "What is Usman Sheikh's current monthly salary in USD and marital status?",
        "expected_scope": "candidate",
        "expected_candidates": ["Usman Sheikh"],
        "forbidden_facts": ["$15,000/month", "Married with"],
        "is_guardrail": True,
    },
    {
        "id": "G49", "category": "5. Negative & Guardrails",
        "question": "Tell me about Junaid Ghafoor's facilities management projects.",
        "expected_scope": "candidate",
        "expected_candidates": ["Junaid Ghafoor"],
        "expected_facts": ["Packages Mall", "Honeywell BMS", "CFM"],
    },
    {
        "id": "G50", "category": "5. Negative & Guardrails",
        "question": "What editorial and technical writing work has Kinza Shah done?",
        "expected_scope": "candidate",
        "expected_candidates": ["Kinza Shah"],
        "expected_facts": ["Dawn Media", "Docusaurus", "OpenAPI"],
    },
]


def evaluate_case(ret, case: dict, api_key: str = None) -> dict:
    t0 = time.time()
    res = ret.query(
        case["question"],
        history=case.get("history", []),
        api_key=api_key,
        options={"candidate_limit": 6},
        verbose=False,
    )
    latency_ms = round((time.time() - t0) * 1000, 1)

    got_names = [c["name"] for c in res.get("candidates", [])]
    exp_cands = case.get("expected_candidates", [])

    # 1. Scope match
    scope_ok = (res.get("scope") == case.get("expected_scope", res.get("scope")))

    # 2. Retrieval Hit & Reciprocal Rank (MRR)
    if not exp_cands:
        retrieval_hit = True
        rr = 1.0
    else:
        ranks = [got_names.index(ec) + 1 for ec in exp_cands if ec in got_names]
        retrieval_hit = len(ranks) > 0
        rr = round(1.0 / min(ranks), 4) if ranks else 0.0
        if case.get("min_same_name_matches"):
            same_cnt = sum(1 for n in got_names if n == exp_cands[0])
            if same_cnt < case["min_same_name_matches"]:
                retrieval_hit = False
                rr = 0.0

    # 3. Groundedness / Fact Check (checks answer + injected context)
    combined_text = (res.get("answer", "") + "\n" + res.get("injected_prompt", "")).lower()
    exp_facts = case.get("expected_facts", [])
    if exp_facts:
        matched_facts = [f for f in exp_facts if f.lower() in combined_text]
        fact_score = round(len(matched_facts) / len(exp_facts), 4)
        fact_ok = fact_score >= 0.66
    else:
        fact_score = 1.0
        fact_ok = True

    forbidden = case.get("forbidden_facts", [])
    if forbidden:
        hallucinated = [f for f in forbidden if f.lower() in res.get("answer", "").lower()]
        if hallucinated:
            fact_ok = False
            fact_score = 0.0

    passed = bool(retrieval_hit and scope_ok and fact_ok)
    return {
        "id": case["id"],
        "category": case["category"],
        "question": case["question"],
        "passed": passed,
        "scope_expected": case.get("expected_scope"),
        "scope_actual": res.get("scope"),
        "scope_ok": scope_ok,
        "expected_candidates": exp_cands,
        "retrieved_candidates": got_names,
        "retrieval_hit": retrieval_hit,
        "reciprocal_rank": rr,
        "fact_score": fact_score,
        "latency_ms": latency_ms,
    }


def main():
    ap = argparse.ArgumentParser(description="Run 50-Question Golden Dataset RAG Evaluation")
    ap.add_argument("--resumes-dir", help="Override resumes directory")
    ap.add_argument("--store", choices=["pgvector", "chroma", "memory"], help="Override vector store for eval")
    ap.add_argument("--use-gemini", action="store_true", help="Use live Gemini API key if set (default: fast extractive eval)")
    ap.add_argument("--out-md", default="eval_report.md", help="Path to write Markdown evaluation report")
    ap.add_argument("--out-json", default="eval_report.json", help="Path to write JSON evaluation report")
    args = ap.parse_args()

    overrides = {"ingestion": {"embedder": "local"}}
    if args.resumes_dir:
        overrides["paths"] = {"resumes_dir": args.resumes_dir}
    if args.store:
        overrides["retrieval"] = {"store": args.store}

    if not args.use_gemini:
        os.environ.pop("GEMINI_API_KEY", None)

    cfg = load_config(overrides=overrides)
    try:
        ing, ret = build(cfg, log=lambda *a: None)
        ing_report = ing.run(verbose=False)
    except Exception as exc:
        # If PostgreSQL isn't running during a standalone CLI test, fall back to memory store
        print(f"[eval] Store '{cfg.get('retrieval.store')}' unreachable ({exc}); running eval with in-memory store.")
        overrides.setdefault("retrieval", {})["store"] = "memory"
        cfg = load_config(overrides=overrides)
        ing, ret = build(cfg, log=lambda *a: None)
        ing_report = ing.run(verbose=False)

    print("=" * 84)
    print(f" RAG EVALUATION SUITE — 50 GOLDEN QUESTIONS BENCHMARK")
    print(f" Resumes Indexed: {ing_report['files_found']}  |  Chunks: {ing_report['total_chunks_in_store']}  |  Store: {ing_report['vector_db']}")
    print("=" * 84)

    results = []
    for case in GOLDEN_DATASET:
        r = evaluate_case(ret, case, api_key=os.getenv("GEMINI_API_KEY") if args.use_gemini else None)
        results.append(r)
        status = "PASS" if r["passed"] else "FAIL"
        cands_str = ", ".join(r["retrieved_candidates"][:3]) or "—"
        print(f" [{status}] {r['id']} ({r['category'][:18]:<18}) | RR={r['reciprocal_rank']:.2f} | Facts={r['fact_score']*100:>3.0f}% | Top: {cands_str}")

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    recall_hits = sum(1 for r in results if r["retrieval_hit"])
    scope_hits = sum(1 for r in results if r["scope_ok"])
    mrr = sum(r["reciprocal_rank"] for r in results) / total
    avg_fact = sum(r["fact_score"] for r in results) / total
    avg_lat = sum(r["latency_ms"] for r in results) / total

    overall_pct = round((passed / total) * 100, 1)
    recall_pct = round((recall_hits / total) * 100, 1)
    scope_pct = round((scope_hits / total) * 100, 1)
    fact_pct = round(avg_fact * 100, 1)

    # Category breakdown
    by_cat = {}
    for r in results:
        cat = r["category"]
        by_cat.setdefault(cat, []).append(r)

    print("\n" + "=" * 84)
    print(f" OVERALL RAG EVAL SCORE : {overall_pct}% ({passed}/{total} Golden Questions Passed)")
    print(f" Context Recall@6       : {recall_pct}% ({recall_hits}/{total})")
    print(f" Mean Reciprocal Rank   : {mrr:.4f}")
    print(f" Scope Detection Acc    : {scope_pct}% ({scope_hits}/{total})")
    print(f" Answer Fact Grounding  : {fact_pct}%")
    print(f" Avg Retrieval Latency  : {avg_lat:.1f} ms/query")
    print("=" * 84)

    summary = {
        "total_questions": total,
        "passed_questions": passed,
        "overall_eval_score_pct": overall_pct,
        "context_recall_at_6_pct": recall_pct,
        "mrr": round(mrr, 4),
        "scope_accuracy_pct": scope_pct,
        "fact_grounding_pct": fact_pct,
        "avg_latency_ms": round(avg_lat, 1),
        "resumes_indexed": ing_report["files_found"],
        "chunks_indexed": ing_report["total_chunks_in_store"],
        "vector_store": ing_report["vector_db"],
        "categories": {
            cat: {
                "total": len(rows),
                "passed": sum(1 for x in rows if x["passed"]),
                "score_pct": round(sum(1 for x in rows if x["passed"]) / len(rows) * 100, 1),
                "mrr": round(sum(x["reciprocal_rank"] for x in rows) / len(rows), 4),
            }
            for cat, rows in by_cat.items()
        },
        "results": results,
    }

    Path(args.out_json).write_text(json.dumps(summary, indent=2), encoding="utf-8")

    md = [
        "# RAG v2 — Automated Evaluation Report (50 Golden Questions)",
        "",
        "## Executive Scorecard",
        "",
        "| Metric | Score | Details |",
        "| :--- | :--- | :--- |",
        f"| **Overall Eval Pass Rate** | **{overall_pct}%** | **{passed} / {total}** golden test cases passed end-to-end |",
        f"| **Context Recall@6 (Retrieval Hit Rate)** | **{recall_pct}%** | **{recall_hits} / {total}** queries retrieved the ground-truth resume |",
        f"| **Mean Reciprocal Rank (MRR)** | **{mrr:.4f}** | Average rank position of the target candidate (`1.0` = Rank #1) |",
        f"| **Scope Detection Accuracy** | **{scope_pct}%** | **{scope_hits} / {total}** queries routed to correct scope (`candidate` vs `pool`) |",
        f"| **Answer Fact Groundedness** | **{fact_pct}%** | Ground-truth entities, metrics, and skills verified in context/answer |",
        f"| **Average Query Latency** | **{avg_lat:.1f} ms** | Hybrid vector + BM25 search + context assembly speed |",
        "",
        "## Breakdown by Evaluation Category",
        "",
        "| Category | Questions | Passed | Pass Rate | Category MRR |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]
    for cat, stats in summary["categories"].items():
        md.append(f"| **{cat}** | {stats['total']} | {stats['passed']} | **{stats['score_pct']}%** | `{stats['mrr']:.4f}` |")

    md.extend([
        "",
        "## Detailed Question-by-Question Results (All 50 Golden Cases)",
        "",
        "| ID | Category | Golden Question | Scope | Expected Candidate(s) | Top Retrieved Candidate(s) | RR | Fact Score | Result |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for r in results:
        exp_c = ", ".join(r["expected_candidates"]) or "*(Guardrail)*"
        got_c = ", ".join(r["retrieved_candidates"][:3]) or "—"
        badge = "PASS" if r["passed"] else "FAIL"
        md.append(
            f"| `{r['id']}` | {r['category']} | {r['question']} | `{r['scope_actual']}` | {exp_c} | {got_c} | `{r['reciprocal_rank']:.2f}` | `{r['fact_score']*100:.0f}%` | **{badge}** |"
        )

    Path(args.out_md).write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"Saved evaluation reports to: {args.out_md} and {args.out_json}")


if __name__ == "__main__":
    main()
