"""Load standard benchmark clauses per contract type, precompute embeddings, diff vs user clauses."""
from __future__ import annotations
from pathlib import Path
import json
import numpy as np

from . import llm

_BENCH: dict[str, list[dict]] = {}
_BENCH_EMB: dict[str, np.ndarray] = {}  # contract_type -> (N_bench, dim)
_LOADED = False


def load_all() -> None:
    global _LOADED
    if _LOADED:
        return
    root = Path(__file__).resolve().parents[2] / "data" / "benchmarks"
    if not root.exists():
        _LOADED = True
        return
    for f in root.glob("*.json"):
        with f.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        ctype = f.stem
        _BENCH[ctype] = data.get("clauses", [])
    # precompute embeddings
    for ctype, items in _BENCH.items():
        if not items:
            continue
        try:
            emb = llm.embed([it["standard_text"] for it in items])
            n = np.linalg.norm(emb, axis=-1, keepdims=True) + 1e-9
            _BENCH_EMB[ctype] = emb / n
        except Exception:
            # skip benchmark embedding on key/network failure — diff just won't run
            pass
    _LOADED = True


def best_match(contract_type: str, clause_type: str, clause_text: str) -> dict | None:
    """Return {standard_text, divergence_score (0-1), label} or None if no benchmark."""
    items = _BENCH.get(contract_type, [])
    mat = _BENCH_EMB.get(contract_type)
    if not items or mat is None:
        return None
    # filter by type if any match, else use all
    typed_idx = [i for i, it in enumerate(items) if it.get("clause_type") == clause_type]
    if not typed_idx:
        return None
    try:
        q = llm.embed_query(clause_text)
        q = q / (np.linalg.norm(q) + 1e-9)
    except Exception:
        return None
    sims = mat[typed_idx] @ q
    best_local = int(np.argmax(sims))
    best_global = typed_idx[best_local]
    sim = float(sims[best_local])
    divergence = max(0.0, min(1.0, 1.0 - sim))
    label = "similar"
    if divergence > 0.45:
        label = "more_restrictive"
    elif divergence > 0.25:
        label = "diverges"
    return {
        "standard_text": items[best_global]["standard_text"],
        "divergence_score": round(divergence, 3),
        "label": label,
    }
