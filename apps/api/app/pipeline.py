"""Sync orchestrator. Runs full pipeline per request, yields stage events.

Stages: extracting → scoring → explaining → done
"""
from __future__ import annotations
from pathlib import Path
from typing import Iterator, Callable
import uuid

from . import parse, scoring, store, benchmarks, rag
from .agents import mega_pro, flash_explainer, flash_adversarial


def run_analysis_text(
    text: str,
    filename: str,
    contract_type_hint: str | None,
    perspective: str,
    on_stage: Callable[[str, dict], None] | None = None,
) -> store.Analysis:
    """Run pipeline directly from text (skip PDF parse). Used by /analyze/text demo endpoint."""
    aid = uuid.uuid4().hex[:12]

    def emit(stage: str, meta: dict | None = None) -> None:
        if on_stage:
            on_stage(stage, meta or {})

    emit("extracting", {"analysisId": aid})
    # synthesize a single-page ParsedDoc
    from .parse import ParsedDoc
    parsed = ParsedDoc(text=text, pages=[text], page_offsets=[0], source_kind="text")
    chunks_raw = parse.chunk_text(parsed.text, parsed.page_offsets)
    return _run_from_parsed(aid, parsed, chunks_raw, filename, contract_type_hint, perspective, emit)


def _find_offsets(doc_text: str, quote: str) -> tuple[int, int]:
    idx = doc_text.find(quote)
    if idx == -1:
        # fallback: try first 80 chars
        head = quote[:80]
        idx = doc_text.find(head)
        if idx == -1:
            return 0, len(quote)
    return idx, idx + len(quote)


def run_analysis(
    tmp_path: Path,
    filename: str,
    contract_type_hint: str | None,
    perspective: str,
    on_stage: Callable[[str, dict], None] | None = None,
) -> store.Analysis:
    """Run pipeline synchronously. Calls on_stage(stage, meta) at each stage transition."""
    aid = uuid.uuid4().hex[:12]

    def emit(stage: str, meta: dict | None = None) -> None:
        if on_stage:
            on_stage(stage, meta or {})

    emit("extracting", {"analysisId": aid})
    parsed = parse.parse(tmp_path, filename)
    chunks_raw = parse.chunk_text(parsed.text, parsed.page_offsets)
    return _run_from_parsed(aid, parsed, chunks_raw, filename, contract_type_hint, perspective, emit)


def _run_from_parsed(aid, parsed, chunks_raw, filename, contract_type_hint, perspective, emit):
    analysis = store.Analysis(
        id=aid,
        filename=filename,
        contract_type=contract_type_hint or "unknown",
        perspective=perspective,
        stage="extracting",
        chunks=[
            store.Chunk(id=f"c{i}", text=c["text"], page_number=c["page_number"],
                        offset_start=c["offset_start"], offset_end=c["offset_end"])
            for i, c in enumerate(chunks_raw)
        ],
    )
    store.ANALYSES[aid] = analysis

    emit("scoring", {"clauseCount": 0})
    mega = mega_pro.run(parsed.text, perspective, contract_type_hint)

    detected_type = mega.get("contract_type", "unknown")
    if detected_type != "unknown":
        analysis.contract_type = detected_type

    clauses: list[store.Clause] = []
    for i, c in enumerate(mega.get("clauses", []) or []):
        text = (c.get("text") or "").strip()
        if not text:
            continue
        ctype = c.get("type", "unknown")
        llm_sev = float(c.get("llm_severity", 0))
        rule_mod, rule_reasons = scoring.rule_modifier(ctype, text, perspective)
        score = scoring.final_score(llm_sev, rule_mod, benchmark_div=None)
        start, end = _find_offsets(parsed.text, text)
        clause = store.Clause(
            id=f"cl{i}",
            type=ctype,
            text=text,
            normalized_text=text,
            source_offset_start=start,
            source_offset_end=end,
            page_number=int(c.get("page_number", 1)),
            risk_score=score["value"],
            risk_label=scoring.label_for(score["value"]),
            risk_components=score["components"],
            top_reasons=list(c.get("top_reasons", []) or []) + rule_reasons,
            affected_interest=c.get("affected_interest", "financial"),
        )
        clauses.append(clause)

    analysis.clauses = clauses

    # document-level score
    scores = [cl.risk_score for cl in clauses]
    doc_score, doc_label = scoring.document_score(scores)
    analysis.overall_score = doc_score
    analysis.overall_label = doc_label
    analysis.top_risk_clause_ids = [
        cl.id for cl in sorted(clauses, key=lambda x: x.risk_score, reverse=True)[:5]
    ]

    emit("explaining", {"clauseCount": len(clauses)})
    # Seed with mega-call rationale as fallback, then enrich Medium+ via Flash explainer
    for cl, src in zip(clauses, mega.get("clauses", [])):
        cl.plain_explanation = src.get("rationale", "")

    flagged = [cl for cl in clauses if cl.risk_score >= 25]
    for cl in flagged:
        try:
            r = flash_explainer.explain(cl.type, cl.text, perspective, cl.risk_label, cl.top_reasons)
            cl.plain_explanation = r.get("plain_explanation", cl.plain_explanation)
            cl.real_world_scenario = r.get("real_world_scenario", "")
            cl.suggested_redline = r.get("suggested_redline", "")
        except Exception:
            # explainer failure is non-fatal — keep fallback rationale
            pass

    # Adversarial pass — surface missed risks. Append as synthetic clauses.
    try:
        adv = flash_adversarial.review(
            parsed.text,
            [{"type": c.type, "text": c.text, "risk_label": c.risk_label, "risk_score": c.risk_score} for c in clauses],
            perspective,
        )
        analysis.contradictions = [c for c in (adv.get("contradictions") or []) if c]
        for j, mr in enumerate(adv.get("missed_risks", []) or []):
            sev = float(mr.get("severity", 50))
            label = scoring.label_for(sev)
            clauses.append(store.Clause(
                id=f"adv{j}",
                type=mr.get("clause_type") or "adversarial_finding",
                text=mr.get("title", "Missed risk"),
                normalized_text=mr.get("title", ""),
                page_number=0,
                risk_score=round(sev, 1),
                risk_label=label,
                risk_components={"llm": sev, "rule": 0.0, "benchmark": 0.0},
                top_reasons=["Surfaced by adversarial reviewer"],
                affected_interest="liability",
                plain_explanation=mr.get("explanation", ""),
            ))
        analysis.clauses = clauses
        # recompute doc score
        scores = [cl.risk_score for cl in clauses]
        doc_score, doc_label = scoring.document_score(scores)
        analysis.overall_score = doc_score
        analysis.overall_label = doc_label
        analysis.top_risk_clause_ids = [
            cl.id for cl in sorted(clauses, key=lambda x: x.risk_score, reverse=True)[:5]
        ]
    except Exception:
        pass

    # Benchmark compare — augment risk_components and refine scores
    try:
        for cl in analysis.clauses:
            diff = benchmarks.best_match(analysis.contract_type, cl.type, cl.text)
            if diff:
                cl.benchmark_diff = diff
                refreshed = scoring.final_score(
                    cl.risk_components.get("llm", cl.risk_score),
                    cl.risk_components.get("rule", 0.0),
                    diff["divergence_score"],
                )
                cl.risk_score = refreshed["value"]
                cl.risk_label = scoring.label_for(cl.risk_score)
                cl.risk_components = refreshed["components"]
        # recompute document score after benchmark refinement
        scores = [cl.risk_score for cl in analysis.clauses]
        doc_score, doc_label = scoring.document_score(scores)
        analysis.overall_score = doc_score
        analysis.overall_label = doc_label
    except Exception:
        pass

    # Build RAG index for downstream chat
    try:
        rag.build_index(aid)
    except Exception:
        pass

    analysis.stage = "complete"
    emit("done", {"analysisId": aid, "overallScore": doc_score, "overallLabel": doc_label})
    return analysis


def run_analysis_streaming(
    tmp_path: Path, filename: str, contract_type_hint: str | None, perspective: str,
) -> Iterator[tuple[str, dict]]:
    """Generator version for SSE."""
    events: list[tuple[str, dict]] = []

    def collect(stage: str, meta: dict) -> None:
        events.append((stage, meta))

    # Run synchronously, then drain events. (Sync pipeline; could be made truly streaming later.)
    run_analysis(tmp_path, filename, contract_type_hint, perspective, on_stage=collect)
    for ev in events:
        yield ev
