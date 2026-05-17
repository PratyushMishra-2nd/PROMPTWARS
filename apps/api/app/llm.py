"""Gemini client wrappers using the modern `google-genai` SDK.

Supports both AI Studio API keys (`AIza...`) and Vertex Express
service-account-bound keys (`AQ...`). The SDK auto-routes based on key prefix.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Iterator

import numpy as np
from google import genai
from google.genai import types

from . import config

log = logging.getLogger("lexguard.llm")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

_client: genai.Client | None = None


def _ensure_client() -> genai.Client:
    global _client
    if _client is None:
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY missing in .env")
        _client = genai.Client(api_key=config.GEMINI_API_KEY)
    return _client


def _strip_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else s
        if s.endswith("```"):
            s = s[: -3]
        if s.startswith("json\n"):
            s = s[5:]
    return s.strip()


def generate_json(
    model: str, system: str, user: str, schema_hint: str = "", max_retries: int = 2
) -> dict:
    """Call Gemini with response_mime_type=application/json. Robust to malformed output."""
    client = _ensure_client()
    prompt = user
    if schema_hint:
        prompt = f"{user}\n\nReturn JSON matching this shape:\n{schema_hint}"

    cfg = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
    )

    last_err: Exception | None = None
    last_raw = ""
    for attempt in range(max_retries + 1):
        try:
            p = prompt if attempt == 0 else (
                f"Your previous response was not valid JSON. Return ONLY a valid JSON object, "
                f"no markdown fences, no prose.\n\n{prompt}"
            )
            resp = client.models.generate_content(model=model, contents=p, config=cfg)
            raw = _strip_fences(resp.text or "")
            last_raw = raw
            log.info("gemini %s attempt %d ok, %d chars", model, attempt, len(raw))
            return json.loads(raw)
        except json.JSONDecodeError as e:
            last_err = e
            log.warning("gemini %s attempt %d JSON parse failed: %s | preview=%r",
                        model, attempt, e, last_raw[:200])
            continue
        except Exception as e:
            last_err = e
            log.error("gemini %s attempt %d failed: %s", model, attempt, e)
            continue
    log.error("gemini %s ALL retries failed. last_err=%s last_raw=%r", model, last_err, last_raw[:300])
    return {"_error": f"json parse failed: {last_err}", "_raw_preview": last_raw[:300]}


def generate_text(model: str, system: str, user: str) -> str:
    client = _ensure_client()
    cfg = types.GenerateContentConfig(system_instruction=system)
    resp = client.models.generate_content(model=model, contents=user, config=cfg)
    return (resp.text or "").strip()


def generate_stream(model: str, system: str, user: str) -> Iterator[str]:
    client = _ensure_client()
    cfg = types.GenerateContentConfig(system_instruction=system)
    for chunk in client.models.generate_content_stream(model=model, contents=user, config=cfg):
        if chunk.text:
            yield chunk.text


def embed(texts: list[str]) -> np.ndarray:
    """Embed a list of texts. Tries batch first, falls back to per-item if SDK rejects."""
    client = _ensure_client()
    if not texts:
        return np.zeros((0, 768), dtype=np.float32)
    cfg = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
    try:
        resp = client.models.embed_content(model=config.GEMINI_EMBED_MODEL, contents=texts, config=cfg)
        return np.array([e.values for e in resp.embeddings], dtype=np.float32)
    except Exception as exc:
        log.info("batch embed failed, falling back to per-item: %s", exc)

    out: list[list[float]] = []
    for t in texts:
        resp = client.models.embed_content(model=config.GEMINI_EMBED_MODEL, contents=t, config=cfg)
        out.append(resp.embeddings[0].values)
    return np.array(out, dtype=np.float32)


def embed_query(text: str) -> np.ndarray:
    client = _ensure_client()
    cfg = types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    resp = client.models.embed_content(model=config.GEMINI_EMBED_MODEL, contents=text, config=cfg)
    return np.array(resp.embeddings[0].values, dtype=np.float32)
