"""Compare two analyses clause-by-clause. Match by (type, fuzzy text)."""
from __future__ import annotations
from . import store
import numpy as np

try:
    from . import llm
    HAS_LLM = True
except Exception:
    HAS_LLM = False


def _norm(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v, axis=-1, keepdims=True) + 1e-9
    return v / n


def _best_match(a: store.Clause, b_clauses: list[store.Clause]) -> tuple[store.Clause | None, float]:
    """Return (best match, similarity 0-1) by type filter + token overlap."""
    candidates = [c for c in b_clauses if c.type == a.type]
    if not candidates:
        return None, 0.0
    if len(candidates) == 1:
        return candidates[0], _jaccard(a.text, candidates[0].text)
    # pick highest jaccard
    best = max(candidates, key=lambda c: _jaccard(a.text, c.text))
    return best, _jaccard(a.text, best.text)


def _jaccard(a: str, b: str) -> float:
    sa = set(a.lower().split())
    sb = set(b.lower().split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def compare(prev_id: str, new_id: str) -> dict:
    prev = store.ANALYSES.get(prev_id)
    new = store.ANALYSES.get(new_id)
    if not prev or not new:
        return {"error": "one or both analyses not found"}

    added: list[dict] = []
    removed: list[dict] = []
    changed: list[dict] = []
    unchanged: list[dict] = []

    matched_new: set[str] = set()

    for old_cl in prev.clauses:
        match, sim = _best_match(old_cl, new.clauses)
        if match is None or sim < 0.2:
            removed.append({
                "clause_id": old_cl.id,
                "type": old_cl.type,
                "text": old_cl.text,
                "risk_label": old_cl.risk_label,
                "risk_score": old_cl.risk_score,
            })
            continue
        matched_new.add(match.id)
        if sim >= 0.85:
            unchanged.append({
                "type": old_cl.type,
                "prev_id": old_cl.id,
                "new_id": match.id,
                "similarity": round(sim, 2),
                "risk_score_delta": round(match.risk_score - old_cl.risk_score, 1),
            })
        else:
            changed.append({
                "type": old_cl.type,
                "prev_id": old_cl.id,
                "new_id": match.id,
                "prev_text": old_cl.text,
                "new_text": match.text,
                "prev_risk_label": old_cl.risk_label,
                "new_risk_label": match.risk_label,
                "prev_risk_score": old_cl.risk_score,
                "new_risk_score": match.risk_score,
                "risk_score_delta": round(match.risk_score - old_cl.risk_score, 1),
                "similarity": round(sim, 2),
            })

    for new_cl in new.clauses:
        if new_cl.id in matched_new:
            continue
        added.append({
            "clause_id": new_cl.id,
            "type": new_cl.type,
            "text": new_cl.text,
            "risk_label": new_cl.risk_label,
            "risk_score": new_cl.risk_score,
        })

    # overall verdict
    overall_delta = round(new.overall_score - prev.overall_score, 1)
    verdict = "neutral"
    if overall_delta > 5:
        verdict = "worse"
    elif overall_delta < -5:
        verdict = "better"

    return {
        "prev_id": prev_id,
        "new_id": new_id,
        "prev_score": prev.overall_score,
        "new_score": new.overall_score,
        "overall_delta": overall_delta,
        "verdict": verdict,
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "summary": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "unchanged": len(unchanged),
        },
    }
