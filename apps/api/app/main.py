from __future__ import annotations
import hashlib
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import config, store, pipeline, report_pdf, benchmarks, ratelimit
from .agents import flash_chat

app = FastAPI(title="LexGuard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
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
    """Save upload to tempfile, return (path, sha256-hex)."""
    suffix = Path(file.filename or "upload").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        data = await file.read()
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


@app.post("/api/v1/analyze")
async def analyze(
    request: Request,
    file: UploadFile = File(...),
    contractType: str | None = Form(None),
    perspective: str = Form("employee"),
) -> dict:
    ratelimit.limit_analyze(request)
    store.evict_stale()
    tmp_path, sha = await _save_upload(file)

    dup = _dedupe_hit(sha, perspective, contractType)
    if dup:
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass

    _dedupe_save(sha, perspective, contractType, analysis.id)
    return {"data": {"analysisId": analysis.id, "analysis": analysis.model_dump()}, "error": None}


@app.post("/api/v1/analyze/text")
def analyze_text(body: AnalyzeTextRequest, request: Request) -> dict:
    """Skip PDF parse — analyze raw pasted text. Demo-friendly."""
    ratelimit.limit_analyze(request)
    store.evict_stale()
    if len(body.text.strip()) < 100:
        raise HTTPException(status_code=400, detail="Text too short to analyze (min 100 chars)")

    sha = hashlib.sha256(body.text.encode()).hexdigest()
    dup = _dedupe_hit(sha, body.perspective, body.contractType)
    if dup:
        return {"data": {"analysisId": dup.id, "analysis": dup.model_dump(), "deduped": True}, "error": None}

    try:
        analysis = pipeline.run_analysis_text(
            text=body.text,
            filename=body.filename,
            contract_type_hint=body.contractType,
            perspective=body.perspective,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {e}")
    _dedupe_save(sha, body.perspective, body.contractType, analysis.id)
    return {"data": {"analysisId": analysis.id, "analysis": analysis.model_dump()}, "error": None}


@app.post("/api/v1/analyze/stream")
async def analyze_stream(
    file: UploadFile = File(...),
    contractType: str | None = Form(None),
    perspective: str = Form("employee"),
):
    """SSE-streamed analysis. Emits stage events, then a `done` event with the analysisId."""
    import json as _json
    import asyncio
    store.evict_stale()
    tmp_path = await _save_upload(file)
    fname = file.filename or "upload"

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_stage(stage: str, meta: dict) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, {"event": stage, "data": _json.dumps(meta)})

    async def run() -> None:
        try:
            analysis = await asyncio.to_thread(
                pipeline.run_analysis, tmp_path, fname, contractType, perspective, on_stage
            )
            await queue.put({"event": "result", "data": _json.dumps({"analysisId": analysis.id})})
        except Exception as e:
            await queue.put({"event": "error", "data": _json.dumps({"message": str(e)})})
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
def get_analysis(analysis_id: str) -> dict:
    a = store.ANALYSES.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found (may have been evicted on restart)")
    return {"data": a.model_dump(), "error": None}


@app.get("/api/v1/analyses/{analysis_id}/report.pdf")
def get_report_pdf(analysis_id: str) -> Response:
    a = store.ANALYSES.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    pdf = report_pdf.render_pdf_bytes(a)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lexguard-{analysis_id}.pdf"'},
    )


@app.post("/api/v1/analyses/{analysis_id}/chat")
def chat(analysis_id: str, body: ChatRequest, request: Request) -> dict:
    ratelimit.limit_chat(request)
    a = store.ANALYSES.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
    try:
        text, citations = flash_chat.answer(analysis_id, body.message, body.history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {e}")
    a.messages.append(store.ChatMessage(role="user", content=body.message))
    a.messages.append(store.ChatMessage(role="assistant", content=text, citations=citations))
    return {"data": {"content": text, "citations": citations}, "error": None}


@app.post("/api/v1/analyses/{analysis_id}/chat/stream")
async def chat_stream(analysis_id: str, body: ChatRequest, request: Request):
    """SSE-streamed chat. Tokens stream as Gemini produces them."""
    import json as _json
    import re
    import asyncio
    ratelimit.limit_chat(request)
    a = store.ANALYSES.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_running_loop()
    full_text_parts: list[str] = []

    def producer() -> None:
        try:
            for tok in flash_chat.answer_stream(analysis_id, body.message, body.history):
                full_text_parts.append(tok)
                loop.call_soon_threadsafe(queue.put_nowait, {"event": "token", "data": _json.dumps({"t": tok})})
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, {"event": "error", "data": _json.dumps({"message": str(e)})})
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
def benchmark(analysis_id: str) -> dict:
    a = store.ANALYSES.get(analysis_id)
    if not a:
        raise HTTPException(status_code=404, detail="Analysis not found")
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


@app.delete("/api/v1/analyses/{analysis_id}")
def delete_analysis(analysis_id: str) -> dict:
    store.ANALYSES.pop(analysis_id, None)
    store.EMBEDDINGS.pop(analysis_id, None)
    return {"data": {"deleted": True}, "error": None}
