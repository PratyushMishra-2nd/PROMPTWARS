"""Risk scoring formula and rulebook."""
from __future__ import annotations
from pathlib import Path
import yaml

_RULEBOOK: dict | None = None


def _load() -> dict:
    global _RULEBOOK
    if _RULEBOOK is None:
        p = Path(__file__).resolve().parents[2] / "data" / "rulebook.yaml"
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                _RULEBOOK = yaml.safe_load(f) or {}
        else:
            _RULEBOOK = {}
    return _RULEBOOK


def rule_modifier(clause_type: str, clause_text: str, perspective: str) -> tuple[float, list[str]]:
    """Return (additive 0-100 modifier, reasons triggered)."""
    rb = _load()
    rules = rb.get("clause_rules", {}).get(clause_type, [])
    mod = 0.0
    reasons: list[str] = []
    text_lower = clause_text.lower()
    for rule in rules:
        kw = rule.get("contains", "").lower()
        if kw and kw in text_lower:
            mod += float(rule.get("bump", 0))
            if rule.get("reason"):
                reasons.append(rule["reason"])

    # perspective weights
    weights = rb.get("perspective_weights", {}).get(perspective, {})
    weight = float(weights.get(clause_type, 1.0))
    mod = mod * weight

    return min(mod, 50.0), reasons


def final_score(llm_severity: float, rule_mod: float, benchmark_div: float | None) -> dict:
    bench_component = (benchmark_div or 0.0) * 100.0
    score = 0.55 * llm_severity + 0.25 * bench_component + 0.20 * rule_mod
    score = max(0.0, min(100.0, score))
    return {
        "value": round(score, 1),
        "components": {
            "llm": round(llm_severity, 1),
            "rule": round(rule_mod, 1),
            "benchmark": round(bench_component, 1),
        },
    }


def label_for(score: float) -> str:
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Medium"
    return "Low"


def document_score(clause_scores: list[float]) -> tuple[float, str]:
    if not clause_scores:
        return 0.0, "Low"
    top5 = sorted(clause_scores, reverse=True)[:5]
    mx = max(clause_scores)
    doc = 0.6 * mx + 0.4 * (sum(top5) / len(top5))
    doc = round(doc, 1)
    return doc, label_for(doc)
