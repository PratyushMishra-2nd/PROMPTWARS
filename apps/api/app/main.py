from __future__ import annotations
import hashlib
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import config, store, pipeline, report_pdf, benchmarks, ratelimit, compare as cmp
from . import security as sec
from . import google_services as gcp
from . import auth as fauth
from . import firestore_store as fs
from .agents import flash_chat

app = FastAPI(title="LexGuard API", version="0.1.0")

app.add_middleware(sec.SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=600,
)


@app.on_event("startup")
def _startup() -> None:
    gcp.setup_cloud_logging()
    try:
        benchmarks.load_all()
    except Exception:
        pass


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


class AnalyzeTextRequest(BaseModel):
    text: str
    contractType: str | None = None
    perspective: str = "employee"
    filename: str = "pasted-contract.txt"


@app.get("/api/v1/health")
def health() -> dict:
    return {"data": {"status": "ok"}, "error": None}


@app.get("/api/v1/contract-types")
def contract_types() -> dict:
    return {"data": {"types": config.CONTRACT_TYPES, "perspectives": config.PERSPECTIVES}, "error": None}


async def _save_upload(file: UploadFile) -> tuple[Path, str]:
    """Validate + persist upload to a tempfile. Returns (path, sha256-hex)."""
    sec.validate_upload(file)
    suffix = Path(file.filename or "upload").suffix.lower() or ".bin"
    data = await file.read()
    sec.validate_size(data)
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        sha = hashlib.sha256(data + (file.filename or "").encode()).hexdigest()
        return Path(tmp.name), sha


def _dedupe_hit(sha: str, perspective: str, contract_type: str | None) -> store.Analysis | None:
    key = f"{sha}|{perspective}|{contract_type or ''}"
    aid = store.DEDUPE.get(key)
    if aid:
        a = store.ANALYSES.get(aid)
        if a:
            return a
        store.DEDUPE.pop(key, None)
    return None


def _dedupe_save(sha: str, perspective: str, contract_type: str | None, aid: str) -> None:
    key = f"{sha}|{perspective}|{contract_type or ''}"
    store.DEDUPE[key] = aid


def _get_owned(analysis_id: str, user: dict | None) -> store.Analysis:
    """Fetch an analysis enforcing ownership.

    Rules:
    - 404 if id unknown (don't leak existence).
    - Anonymous analyses (owner_uid is None) accessible by anyone (legacy demo).
    - Owned analyses require matching uid; else 404 (avoid existence oracle).
    """
    a = store.ANALYSES.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    if a.owner_uid is not None:
        if not user or user.get("uid") != a.owner_uid:
            raise HTTPException(status_code=404, detail="Analysis not found")
    return a


@app.post("/api/v1/analyze")
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    contractType: str | None = Form(None),
    perspective: str = Form("employee"),
    user: dict | None = Depends(fauth.current_user),
) -> dict:
    ratelimit.limit_analyze(request, user)
    store.evict_stale()
    tmp_path, sha = await _save_upload(file)
    uid = user["uid"] if user else None

    dup = _dedupe_hit(sha, perspective, contractType)
    if dup and dup.owner_uid == uid:
        tmp_path.unlink(missing_ok=True)
        return {"data": {"analysisId": dup.id, "analysis": dup.model_dump(), "deduped": True}, "error": None}

    try:
        analysis = pipeline.run_analysis(
            tmp_path=tmp_path,
            filename=file.filename or "upload",
            contract_type_hint=contractType,
            perspective=perspective,
        )
    except NotImplementedError as e:
        raise HTTPException(status_code=415, detail=str(e))
    except Exception:
        log = __import__("logging").getLogger("lexguard.api")
        log.exception("pipeline failed")
        raise HTTPException(status_code=500, detail="Pipeline failed")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    analysis.owner_uid = uid
    _dedupe_save(sha, perspective, contractType, analysis.id)
    if user:
        fs.save_analysis(user["uid"], analysis.id, analysis.model_dump())
    return {"data": {"analysisId": analysis.id, "analysis": analysis.model_dump()}, "error": None}


@app.post("/api/v1/analyze/text")
async def analyze_text(
    body: AnalyzeTextRequest,
    request: Request,
    user: dict | None = Depends(fauth.current_user),
) -> dict:
    """Skip PDF parse — analyze raw pasted text. Demo-friendly."""
    ratelimit.limit_analyze(request, user)
    store.evict_stale()
    sec.validate_text_length(body.text)
    if len(body.text.strip()) < 100:
        raise HTTPException(status_code=400, detail="Text too short to analyze (min 100 chars)")

    uid = user["uid"] if user else None
    sha = hashlib.sha256(body.text.encode()).hexdigest()
    dup = _dedupe_hit(sha, body.perspective, body.contractType)
    if dup and dup.owner_uid == uid:
        return {"data": {"analysisId": dup.id, "analysis": dup.model_dump(), "deduped": True}, "error": None}

    try:
        analysis = pipeline.run_analysis_text(
            text=body.text,
            filename=body.filename,
            contract_type_hint=body.contractType,
            perspective=body.perspective,
        )
    except Exception:
        log = __import__("logging").getLogger("lexguard.api")
        log.exception("pipeline failed")
        raise HTTPException(status_code=500, detail="Pipeline failed")
    analysis.owner_uid = uid
    _dedupe_save(sha, body.perspective, body.contractType, analysis.id)
    if user:
        fs.save_analysis(user["uid"], analysis.id, analysis.model_dump())
    return {"data": {"analysisId": analysis.id, "analysis": analysis.model_dump()}, "error": None}


@app.get("/api/v1/me/analyses")
def my_analyses(user: dict | None = Depends(fauth.current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    items = fs.list_user_analyses(user["uid"])
    return {"data": {"analyses": items, "user": user}, "error": None}


@app.delete("/api/v1/me/analyses/{analysis_id}")
def delete_my_analysis(analysis_id: str, user: dict | None = Depends(fauth.current_user)) -> dict:
    if not user:
        raise HTTPException(status_code=401, detail="Sign in required")
    fs.delete_user_analysis(user["uid"], analysis_id)
    store.ANALYSES.pop(analysis_id, None)
    store.EMBEDDINGS.pop(analysis_id, None)
    return {"data": {"deleted": True}, "error": None}


@app.post("/api/v1/analyze/stream")
async def analyze_stream(
    file: UploadFile = File(...),
    contractType: str | None = Form(None),
    perspective: str = Form("employee"),
    user: dict | None = Depends(fauth.current_user),
):
    """SSE-streamed analysis. Emits stage events, then a `done` event with the analysisId."""
    import json as _json
    import asyncio
    store.evict_stale()
    tmp_path, _sha = await _save_upload(file)
    fname = file.filename or "upload"
    uid = user["uid"] if user else None

    queue: asyncio.Queue = asyncio.Queue(maxsize=64)
    loop = asyncio.get_running_loop()

    def on_stage(stage: str, meta: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"event": stage, "data": _json.dumps(meta)})

    async def run() -> None:
        try:
            analysis = await asyncio.to_thread(
                pipeline.run_analysis, tmp_path, fname, contractType, perspective, on_stage
            )
            analysis.owner_uid = uid
            if user:
                fs.save_analysis(user["uid"], analysis.id, analysis.model_dump())
            await queue.put({"event": "result", "data": _json.dumps({"analysisId": analysis.id})})
        except Exception:
            log = __import__("logging").getLogger("lexguard.api")
            log.exception("analyze stream failed")
            await queue.put({"event": "error", "data": _json.dumps({"message": "Pipeline failed"})})
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            await queue.put({"event": "close", "data": "{}"})

    asyncio.create_task(run())

    async def events():
        while True:
            ev = await queue.get()
            if ev["event"] == "close":
                break
            yield ev

    return EventSourceResponse(events())


@app.get("/api/v1/analyses/{analysis_id}")
def get_analysis(analysis_id: str, user: dict | None = Depends(fauth.current_user)) -> dict:
    a = _get_owned(analysis_id, user)
    return {"data": a.model_dump(), "error": None}


@app.get("/api/v1/clauses/{analysis_id}/{clause_id}/tts.mp3")
def clause_tts(analysis_id: str, clause_id: str, user: dict | None = Depends(fauth.current_user)) -> Response:
    """Synthesize a clause's plain-language explanation as MP3 (Google Cloud TTS)."""
    a = _get_owned(analysis_id, user)
    clause = next((c for c in a.clauses if c.id == clause_id), None)
    if not clause:
        raise HTTPException(status_code=404, detail="Clause not found")
    text = clause.plain_explanation or clause.text
    audio = gcp.tts_synthesize(text)
    if audio is None:
        raise HTTPException(
            status_code=503,
            detail="Text-to-Speech disabled. Set ENABLE_TTS=1 + GCP_PROJECT_ID env vars.",
        )
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "public, max-age=3600",
            "Content-Disposition": f'inline; filename="{clause_id}.mp3"',
        },
    )


@app.get("/api/v1/services/status")
def services_status() -> dict:
    """Report which Google services are wired. Powers the UI badge row."""
    return {"data": {
        "gemini": bool(config.GEMINI_API_KEY),
        "cloud_logging": gcp.ENABLE_CLOUD_LOGGING and bool(gcp.GCP_PROJECT_ID),
        "tts": gcp.ENABLE_TTS,
        "translation": gcp.ENABLE_TRANSLATION,
        "document_ai": bool(gcp.GCP_PROJECT_ID and gcp.DOCAI_PROCESSOR_ID),
        "firebase_auth": fauth.ENABLE_FIREBASE,
        "firestore": fs.ENABLE_FIRESTORE,
    }, "error": None}


@app.get("/api/v1/analyses/{analysis_id}/export.json")
def export_json(analysis_id: str, user: dict | None = Depends(fauth.current_user)) -> Response:
    a = _get_owned(analysis_id, user)
    import json as _json
    body = _json.dumps(a.model_dump(), indent=2).encode()
    return Response(content=body, media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="lexguard-{analysis_id}.json"'})


@app.get("/api/v1/analyses/{analysis_id}/export.csv")
def export_csv(analysis_id: str, user: dict | None = Depends(fauth.current_user)) -> Response:
    a = _get_owned(analysis_id, user)
    import csv, io
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "type", "risk_label", "risk_score", "confidence", "page",
                "affected_interest", "top_reasons", "text", "plain_explanation", "suggested_redline"])
    for c in sorted(a.clauses, key=lambda x: x.risk_score, reverse=True):
        w.writerow([
            c.id, c.type, c.risk_label, c.risk_score, round(c.confidence, 2), c.page_number,
            c.affected_interest, " | ".join(c.top_reasons), c.text,
            c.plain_explanation, c.suggested_redline,
        ])
    return Response(content=buf.getvalue().encode("utf-8-sig"), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="lexguard-{analysis_id}.csv"'})


@app.get("/api/v1/analyses/{analysis_id}/report.pdf")
def get_report_pdf(analysis_id: str, user: dict | None = Depends(fauth.current_user)) -> Response:
    a = _get_owned(analysis_id, user)
    pdf = report_pdf.render_pdf_bytes(a)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lexguard-{analysis_id}.pdf"'},
    )


@app.post("/api/v1/analyses/{analysis_id}/chat")
def chat(analysis_id: str, body: ChatRequest, request: Request,
         user: dict | None = Depends(fauth.current_user)) -> dict:
    ratelimit.limit_chat(request, user)
    a = _get_owned(analysis_id, user)
    try:
        text, citations = flash_chat.answer(analysis_id, body.message, body.history)
    except Exception:
        log = __import__("logging").getLogger("lexguard.api")
        log.exception("chat failed")
        raise HTTPException(status_code=500, detail="Chat failed")
    a.messages.append(store.ChatMessage(role="user", content=body.message))
    a.messages.append(store.ChatMessage(role="assistant", content=text, citations=citations))
    return {"data": {"content": text, "citations": citations}, "error": None}


@app.post("/api/v1/analyses/{analysis_id}/chat/stream")
async def chat_stream(analysis_id: str, body: ChatRequest, request: Request,
                      user: dict | None = Depends(fauth.current_user)):
    """SSE-streamed chat. Tokens stream as Gemini produces them."""
    import json as _json
    import re
    import asyncio
    ratelimit.limit_chat(request, user)
    a = _get_owned(analysis_id, user)

    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    loop = asyncio.get_running_loop()
    full_text_parts: list[str] = []

    def producer() -> None:
        try:
            for tok in flash_chat.answer_stream(analysis_id, body.message, body.history):
                full_text_parts.append(tok)
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "token", "data": _json.dumps({"t": tok})})
        except Exception:
            log = __import__("logging").getLogger("lexguard.api")
            log.exception("chat stream failed")
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "error", "data": _json.dumps({"message": "Chat failed"})})
        finally:
            full = "".join(full_text_parts)
            # extract clause ids the model cited
            found = re.findall(r"\[([a-zA-Z0-9]+)\]", full)
            valid_ids = {c.id for c in a.clauses} | {c.id for c in a.chunks}
            cits = [c for c in found if c in valid_ids]
            # persist conversation
            a.messages.append(store.ChatMessage(role="user", content=body.message))
            a.messages.append(store.ChatMessage(role="assistant", content=full, citations=cits))
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "done", "data": _json.dumps({"citations": cits})})
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "close", "data": "{}"})

    asyncio.create_task(asyncio.to_thread(producer))

    async def events():
        while True:
            ev = await queue.get()
            if ev["event"] == "close":
                break
            yield ev

    return EventSourceResponse(events())


@app.get("/api/v1/analyses/{analysis_id}/benchmark")
def benchmark(analysis_id: str, user: dict | None = Depends(fauth.current_user)) -> dict:
    a = _get_owned(analysis_id, user)
    diffs = []
    for c in a.clauses:
        if c.benchmark_diff:
            diffs.append({
                "clause_id": c.id,
                "clause_type": c.type,
                "user_text": c.text,
                "standard_text": c.benchmark_diff["standard_text"],
                "divergence_score": c.benchmark_diff["divergence_score"],
                "label": c.benchmark_diff["label"],
                "risk_label": c.risk_label,
                "risk_score": c.risk_score,
            })
    return {"data": {"contract_type": a.contract_type, "diffs": diffs}, "error": None}


@app.get("/api/v1/analyses")
def list_analyses(user: dict | None = Depends(fauth.current_user)) -> dict:
    """List analyses owned by caller (or anonymous bucket when auth disabled)."""
    uid = user["uid"] if user else None
    items = sorted(
        [
            {
                "id": a.id,
                "filename": a.filename,
                "contract_type": a.contract_type,
                "perspective": a.perspective,
                "overall_score": a.overall_score,
                "overall_label": a.overall_label,
                "clause_count": len(a.clauses),
                "created_at": a.created_at,
            }
            for a in store.ANALYSES.values()
            if a.owner_uid == uid
        ],
        key=lambda x: x["created_at"],
        reverse=True,
    )
    return {"data": {"analyses": items}, "error": None}


@app.get("/api/v1/compare")
def compare_versions(prev: str, new: str, user: dict | None = Depends(fauth.current_user)) -> dict:
    if prev == new:
        raise HTTPException(status_code=400, detail="prev and new are the same analysis")
    _get_owned(prev, user)  # ownership check; raises 404 if not allowed
    _get_owned(new, user)
    result = cmp.compare(prev, new)
    if result.get("error"):
        raise HTTPException(status_code=404, detail=result["error"])
    return {"data": result, "error": None}


@app.delete("/api/v1/analyses/{analysis_id}")
def delete_analysis(analysis_id: str, user: dict | None = Depends(fauth.current_user)) -> dict:
    _get_owned(analysis_id, user)  # 404 if missing or not owner
    store.ANALYSES.pop(analysis_id, None)
    store.EMBEDDINGS.pop(analysis_id, None)
    return {"data": {"deleted": True}, "error": None}
