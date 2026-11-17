import json
import os
import re
import threading
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from rag_core import NothingIndexed
from rag_core.embeddings import resolve_api_key
from . import services


# ---------------------------------------------------------------- helpers
def _cors(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    response["Access-Control-Allow-Headers"] = "Content-Type, X-Gemini-Api-Key"
    return response


def api(methods):
    """CORS + OPTIONS + method check + error JSON, so each view stays tiny."""
    def deco(fn):
        @csrf_exempt
        def wrapper(request, *a, **kw):
            if request.method == "OPTIONS":
                return _cors(HttpResponse(status=204))
            if request.method not in methods:
                return _cors(JsonResponse({"error": f"{' / '.join(methods)} required"}, status=405))
            try:
                return _cors(fn(request, *a, **kw))
            except NothingIndexed as e:
                return _cors(JsonResponse({"error": str(e), "code": "nothing_indexed"}, status=409))
            except Exception as e:
                return _cors(JsonResponse({"error": f"{type(e).__name__}: {e}"}, status=500))
        return wrapper
    return deco


def _body(request) -> dict:
    try:
        return json.loads(request.body.decode("utf-8")) if request.body else {}
    except json.JSONDecodeError:
        return {}


def _api_key(request, body=None) -> str:
    body = body or {}
    return resolve_api_key(body.get("api_key") or request.headers.get("X-Gemini-Api-Key", "").strip())


# ---------------------------------------------------------------- INGESTION API
@api(["POST"])
def ingest_view(request):
    """Start ingestion. Body: {"force": false, "wait": false, "only": ["file.pdf"]}"""
    _, ingestion, _ = services.get()
    body = _body(request)
    key = _api_key(request, body)
    kwargs = dict(force=bool(body.get("force")), api_key=key, only=body.get("only") or None, verbose=True)
    if ingestion.status["state"] == "running":
        return JsonResponse({"started": False, "status": ingestion.status}, status=409)
    if body.get("wait"):
        return JsonResponse(ingestion.run(**kwargs))
    threading.Thread(target=lambda: _safe_run(ingestion, kwargs), daemon=True).start()
    return JsonResponse({"started": True, "status": ingestion.status}, status=202)


def _safe_run(ingestion, kwargs):
    try:
        ingestion.run(**kwargs)
    except Exception as exc:
        print(f"[ingest] failed: {exc}")


@api(["GET"])
def ingest_status_view(request):
    _, ingestion, _ = services.get()
    return JsonResponse(ingestion.status)


@api(["POST"])
def reingest_view(request):
    """Backwards-compatible: forced, synchronous full re-index."""
    _, ingestion, _ = services.get()
    report = ingestion.run(force=True, api_key=_api_key(request, _body(request)), verbose=True)
    report["chunk_count"] = report.get("total_chunks_in_store")
    report["total_ingest_time_s"] = report.get("total_time_s")
    report["embedding_model"] = report.get("embedder")
    return JsonResponse(report)


@api(["POST"])
def upload_view(request):
    """multipart/form-data: files=<resume files...>; optional ingest=true to index immediately."""
    config, ingestion, _ = services.get()
    exts = {e.lower() for e in config.get("ingestion.extensions", [])}
    max_bytes = float(config.get("ingestion.max_file_mb", 15)) * 1024 * 1024
    saved, rejected = [], []
    dest_dir = ingestion.ws.resumes_dir
    for f in request.FILES.getlist("files"):
        name = re.sub(r"[^\w.\- ]", "_", os.path.basename(f.name)).strip() or "resume"
        if os.path.splitext(name)[1].lower() not in exts:
            rejected.append({"file": f.name, "reason": "unsupported file type"})
        elif f.size > max_bytes:
            rejected.append({"file": f.name, "reason": "file too large"})
        else:
            target = dest_dir / name
            n = 1
            while target.exists() and request.POST.get("overwrite") != "true":
                target = dest_dir / f"{Path(name).stem}_{n}{Path(name).suffix}"
                n += 1
            with open(target, "wb") as out:
                for chunk in f.chunks():
                    out.write(chunk)
            saved.append(target.name)
    resp = {"saved": saved, "rejected": rejected}
    if saved and request.POST.get("ingest", "true") != "false" and ingestion.status["state"] != "running":
        key = _api_key(request)
        threading.Thread(target=lambda: _safe_run(ingestion, dict(api_key=key, verbose=True)), daemon=True).start()
        resp["ingest_started"] = True
    return JsonResponse(resp, status=201 if saved else 400)


@api(["GET"])
def candidates_view(request):
    _, ingestion, retrieval = services.get()
    try:
        _, eid = retrieval._resolve(_api_key(request))
    except NothingIndexed:
        return JsonResponse({"total": 0, "candidates": []})
    cands = ingestion.ws.candidates(eid)
    return JsonResponse({"total": len(cands), "candidates": cands})


@api(["DELETE", "POST"])
def candidate_detail_view(request, source):
    """DELETE /api/candidates/<file name>  -> remove the resume from the index and from disk."""
    _, ingestion, _ = services.get()
    ok = ingestion.remove(source, delete_file=True)
    return JsonResponse({"removed": ok, "source": source}, status=200 if ok else 404)


# ---------------------------------------------------------------- RETRIEVAL API
@api(["POST"])
def query_view(request):
    _, _, retrieval = services.get()
    body = _body(request)
    user_query = (body.get("query") or "").strip()
    if not user_query:
        return JsonResponse({"error": "Missing 'query' field"}, status=400)
    history = body.get("history") if isinstance(body.get("history"), list) else []
    options = {  # every retrieval setting can be overridden per request
        k: body.get(k) for k in ("candidate_limit", "max_chunks_per_candidate", "candidates", "candidate_detection",
                                 "profile_mode", "fetch_k", "weights", "context_max_chars") if k in body}
    if "top_k" in body and "max_chunks_per_candidate" not in options:   # old frontend field
        try:
            options["max_chunks_per_candidate"] = max(1, min(int(body["top_k"]), 12))
        except (TypeError, ValueError):
            pass
    return JsonResponse(retrieval.query(user_query, history=history, api_key=_api_key(request, body),
                                        options=options, verbose=True))


@api(["GET"])
def chunks_view(request):
    _, ingestion, retrieval = services.get()
    out = retrieval.list_chunks(candidate_id=request.GET.get("candidate") or None,
                                limit=min(int(request.GET.get("limit", 300)), 2000))
    return JsonResponse(out)


# ---------------------------------------------------------------- status / config
@api(["GET"])
def health_view(request):
    config, ingestion, retrieval = services.get()
    key = resolve_api_key()
    info = {"status": "ok", "framework": "Django + WhiteNoise", "has_env_api_key": bool(key),
            "ingestion_state": ingestion.status["state"], "resumes_dir": str(ingestion.ws.resumes_dir)}
    try:
        emb, eid = retrieval._resolve(key)
        index = retrieval._index(eid)
        info.update(candidates_indexed=len(index.candidates), chunks_indexed=index.size, embedding_model=eid,
                    vector_db=ingestion.ws.store_for(eid).name, indexed=True)
    except NothingIndexed:
        info.update(candidates_indexed=0, chunks_indexed=0, indexed=False)
    return JsonResponse(info)


@api(["GET"])
def config_view(request):
    config, _, _ = services.get()
    return JsonResponse(config.public_dict())


def spa_index_view(request):
    index_file = settings.FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(open(index_file, "rb"), content_type="text/html; charset=utf-8")
    return HttpResponse("Frontend build not found in backend/frontend_dist/index.html. "
                        "Run 'python manage.py build_frontend'.", status=404)
