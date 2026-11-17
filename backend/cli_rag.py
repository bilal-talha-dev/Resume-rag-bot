"""
Standalone command line for both pipelines (no Django needed).

  python cli_rag.py ingest                 # incremental: only new / changed / deleted resumes
  python cli_rag.py ingest --force         # re-index everything
  python cli_rag.py candidates             # list indexed resumes
  python cli_rag.py ask "Who knows Terraform?"  [--limit 10] [--candidate "Ali Khan"]
  python cli_rag.py chat                   # interactive, keeps conversation history
"""
import argparse
import json
import sys

from rag_core import NothingIndexed, build, load_config


def main():
    ap = argparse.ArgumentParser(description="Resume RAG — ingestion & retrieval pipelines")
    ap.add_argument("--config", help="path to a rag_config.yaml (default: backend/rag_config.yaml)")
    ap.add_argument("--resumes-dir", help="override paths.resumes_dir")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ingest"); p.add_argument("--force", action="store_true"); p.add_argument("--json", action="store_true")
    sub.add_parser("candidates")
    for name in ("ask", "chat"):
        q = sub.add_parser(name)
        if name == "ask":
            q.add_argument("question", nargs="+")
        q.add_argument("--limit", type=int, help="max candidates sent to the LLM")
        q.add_argument("--candidate", action="append", help="restrict to this candidate (name or id), repeatable")
        q.add_argument("--prompt", action="store_true", help="print the exact prompt sent to the LLM")
    a = ap.parse_args()

    overrides = {"paths": {"resumes_dir": a.resumes_dir}} if a.resumes_dir else None
    ingestion, retrieval = build(load_config(path=a.config, overrides=overrides))

    if a.cmd == "ingest":
        r = ingestion.run(force=a.force, verbose=not a.json)
        if a.json:
            print(json.dumps(r, indent=1))
        else:
            print(f"\nDone: {r['ingested']} ingested, {r['skipped_unchanged']} unchanged, {r['removed']} removed, "
                  f"{r['failed']} failed — {r['total_chunks_in_store']} chunks in store ({r['total_time_s']}s, {r['embedder']})")
            for w in r["warnings"]:
                print("  WARN:", w)
            for f in r["failures"]:
                print(f"  FAILED {f['source']}: {f['error']}")
        return

    try:
        if a.cmd == "candidates":
            _, eid = retrieval._resolve(None)
            for c in ingestion.ws.candidates(eid):
                print(f"{c['name']:<28} {c.get('email',''):<34} {c['chunks']:>3} chunks  {c['source']}")
            return

        options = {"candidate_limit": a.limit, "candidates": a.candidate}

        def ask(question, history):
            res = retrieval.query(question, history=history, options=options, verbose=False)
            who = ", ".join(c["name"] for c in res["candidates"]) or "—"
            print(f"\n[{res['scope']} scope · {res['context_mode']} · {len(res['candidates'])}/{res['total_candidates']} resumes: {who}]")
            if a.prompt:
                print(res["injected_prompt"])
            print("\n" + res["answer"] + "\n")
            return res["answer"]

        if a.cmd == "ask":
            ask(" ".join(a.question), [])
        else:
            history = []
            while True:
                try:
                    q = input("you> ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if q.lower() in ("", "exit", "quit"):
                    break
                ans = ask(q, history)
                history += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]
    except NothingIndexed as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
