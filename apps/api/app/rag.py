"""In-memory RAG retrieval. numpy cosine over chunk embeddings."""
from __future__ import annotations
import numpy as np
from . import llm, store


def _normalize(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x, axis=-1, keepdims=True) + 1e-9
    return x / n


def build_index(analysis_id: str) -> None:
    a = store.ANALYSES.get(analysis_id)
    if not a or not a.chunks:
        return
    texts = [c.text for c in a.chunks]
    emb = llm.embed(texts)
    store.EMBEDDINGS[analysis_id] = _normalize(emb)


def retrieve(analysis_id: str, query: str, k: int = 6) -> list[store.Chunk]:
    a = store.ANALYSES.get(analysis_id)
    if not a or not a.chunks:
        return []
    mat = store.EMBEDDINGS.get(analysis_id)
    if mat is None:
        build_index(analysis_id)
        mat = store.EMBEDDINGS.get(analysis_id)
        if mat is None:
            return a.chunks[:k]
    q = _normalize(llm.embed_query(query).reshape(1, -1))[0]
    sims = mat @ q
    top_idx = np.argsort(-sims)[:k]
    return [a.chunks[i] for i in top_idx]
