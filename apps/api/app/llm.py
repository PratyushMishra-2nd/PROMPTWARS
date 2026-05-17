"""Gemini client wrappers. Single AI Studio key for hackathon."""
from __future__ import annotations
import json
import google.generativeai as genai
import numpy as np

from . import config

_configured = False


def _ensure_configured() -> None:
    global _configured
    if not _configured:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY missing in .env")
        genai.configure(api_key=config.GEMINI_API_KEY)
        _configured = True


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s
        if s.endswith("```"):
            s = s[: -3]
        if s.startswith("json\n"):
            s = s[5:]
    return s.strip()


def generate_json(model: str, system: str, user: str, schema_hint: str = "", max_retries: int = 2) -> dict:
    """Call Gemini with response_mime_type=application/json. Robust to malformed output."""
    _ensure_configured()
    m = genai.GenerativeModel(
        model_name=model,
        system_instruction=system,
        generation_config={"response_mime_type": "application/json"},
    )
    prompt = user
    if schema_hint:
        prompt = f"{user}\n\nReturn JSON matching this shape:\n{schema_hint}"

    last_err: Exception | None = None
    last_raw = ""
    for attempt in range(max_retries + 1):
        try:
            p = prompt if attempt == 0 else (
                f"Your previous response was not valid JSON. Return ONLY a valid JSON object, no markdown fences, no prose.\n\n{prompt}"
            )
            resp = m.generate_content(p)
            raw = _strip_fences(resp.text or "")
            last_raw = raw
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            continue
    # final degraded path — return empty shape
    return {"_error": f"json parse failed: {last_err}", "_raw_preview": last_raw[:300]}


def generate_text(model: str, system: str, user: str) -> str:
    _ensure_configured()
    m = genai.GenerativeModel(model_name=model, system_instruction=system)
    resp = m.generate_content(user)
    return (resp.text or "").strip()


def generate_stream(model: str, system: str, user: str):
    _ensure_configured()
    m = genai.GenerativeModel(model_name=model, system_instruction=system)
    for chunk in m.generate_content(user, stream=True):
        if chunk.text:
            yield chunk.text


def embed(texts: list[str]) -> np.ndarray:
    _ensure_configured()
    out: list[list[float]] = []
    # batched single calls (text-embedding-004 accepts one at a time via this API)
    for t in texts:
        r = genai.embed_content(model=config.GEMINI_EMBED_MODEL, content=t, task_type="retrieval_document")
        out.append(r["embedding"])
    return np.array(out, dtype=np.float32)


def embed_query(text: str) -> np.ndarray:
    _ensure_configured()
    r = genai.embed_content(model=config.GEMINI_EMBED_MODEL, content=text, task_type="retrieval_query")
    return np.array(r["embedding"], dtype=np.float32)
