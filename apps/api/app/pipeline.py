"""Synchronous contract-analysis orchestrator.

The pipeline runs each upload through these stages, calling the supplied
`on_stage(stage_name, meta_dict)` callback at each transition so a
streaming endpoint can surface progress to the client:

    extracting -> scoring -> explaining -> done

Each step is best-effort: a failure in (e.g.) the adversarial reviewer
does not abort the whole analysis — it just leaves that section empty
and logs the error. The mega-extraction step is the only hard requirement;
if it fails, the analysis is marked `error` and returned early.
"""
from __future__ import annotations
import logging
import uuid
from pathlib import Path
from typing import Callable, Iterator

from . import benchmarks, parse, rag, scoring, store
from .agents import flash_adversarial, flash_explainer, mega_pro

log = logging.getLogger("lexguard.pipeline")


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
    """Locate a quoted clause inside the source document.

    Tries an exact substring match first, then falls back to matching the
    first 80 characters. Returns ``(0, len(quote))`` if no match — the
    UI gracefully handles missing offsets.
    """
    idx = doc_text.find(quote)
    if idx == -1:
        head = quote[:80]
        idx = doc_text.find(head)
        if idx == -1:
            return 0, len(quote)
    return idx, idx + len(quote)


def _enrich_with_explainer(clauses: list[store.Clause], perspective: str) -> None:
    """Run Flash explainer on each Medium+ clause in parallel for ~4x speedup."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    flagged = [cl for cl in clauses if cl.risk_score >= 25]
    if not flagged:
        return

    def _job(cl: store.Clause) -> tuple[store.Clause, dict | None]:
        try:
            return cl, flash_explainer.explain(
                cl.type, cl.text, perspective, cl.risk_label, cl.top_reasons
            )
        except Exception as exc:
            log.warning("explainer failed for clause %s: %s", cl.id, exc)
            return cl, None

    # Cap parallelism — Gemini free tier rate-limits Flash to ~15 RPM
    max_workers = min(6, len(flagged))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for future in as_completed([pool.submit(_job, cl) for cl in flagged]):
            cl, result = future.result()
            if result is None:
                continue
            cl.plain_explanation = result.get("plain_explanation", cl.plain_explanation)
            cl.real_world_scenario = result.get("real_world_scenario", "")
            cl.suggested_redline = result.get("suggested_redline", "")


def _apply_adversarial_pass(
    analysis: store.Analysis, perspective: str, doc_text: str
) -> None:
    """Run adversarial reviewer; append synthetic clauses + contradictions."""
    try:
        adv = flash_adversarial.review(
            doc_text,
            [
                {"type": c.type, "text": c.text, "risk_label": c.risk_label, "risk_score": c.risk_score}
                for c in analysis.clauses
            ],
            perspective,
        )
    except Exception as exc:
        log.warning("adversarial pass failed: %s", exc)
        return

    analysis.contradictions = [c for c in (adv.get("contradictions") or []) if c]
    for j, mr in enumerate(adv.get("missed_risks") or []):
        sev = float(mr.get("severity", 50))
        analysis.clauses.append(store.Clause(
            id=f"adv{j}",
            type=mr.get("clause_type") or "adversarial_finding",
            text=mr.get("title", "Missed risk"),
            normalized_text=mr.get("title", ""),
            page_number=0,
            risk_score=round(sev, 1),
            risk_label=scoring.label_for(sev),
            risk_components={"llm": sev, "rule": 0.0, "benchmark": 0.0},
            top_reasons=["Surfaced by adversarial reviewer"],
            affected_interest="liability",
            plain_explanation=mr.get("explanation", ""),
            confidence=0.7,
        ))


def _apply_benchmark_diff(analysis: store.Analysis) -> None:
    """Augment each clause with a benchmark divergence + refine risk score."""
    for cl in analysis.clauses:
        try:
            diff = benchmarks.best_match(analysis.contract_type, cl.type, cl.text)
        except Exception as exc:
            log.debug("benchmark lookup failed for %s: %s", cl.id, exc)
            continue
        if not diff:
            continue
        cl.benchmark_diff = diff
        refreshed = scoring.final_score(
            cl.risk_components.get("llm", cl.risk_score),
            cl.risk_components.get("rule", 0.0),
            diff["divergence_score"],
        )
        cl.risk_score = refreshed["value"]
        cl.risk_label = scoring.label_for(cl.risk_score)
        cl.risk_components = refreshed["components"]


def _recompute_document_score(analysis: store.Analysis) -> None:
    scores = [cl.risk_score for cl in analysis.clauses]
    doc_score, doc_label = scoring.document_score(scores)
    analysis.overall_score = doc_score
    analysis.overall_label = doc_label
    analysis.top_risk_clause_ids = [
        cl.id for cl in sorted(analysis.clauses, key=lambda x: x.risk_score, reverse=True)[:5]
    ]


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

    if mega.get("_error"):
        analysis.error_message = f"Extraction failed: {mega['_error']}. Raw preview: {mega.get('_raw_preview', '')}"
        analysis.stage = "error"
        emit("error", {"message": analysis.error_message})
        return analysis

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
            confidence=float(c.get("confidence", 0.8)),
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
    # Seed with mega-call rationale as fallback before Flash enrichment
    for cl, src in zip(clauses, mega.get("clauses", []), strict=False):
        cl.plain_explanation = src.get("rationale", "")

    _enrich_with_explainer(clauses, perspective)
    _apply_adversarial_pass(analysis, perspective, parsed.text)
    _recompute_document_score(analysis)
    _apply_benchmark_diff(analysis)
    _recompute_document_score(analysis)

    try:
        rag.build_index(aid)
    except Exception as exc:
        log.warning("RAG index build failed for %s: %s", aid, exc)

    analysis.stage = "complete"
    emit("done", {
        "analysisId": aid,
        "overallScore": analysis.overall_score,
        "overallLabel": analysis.overall_label,
    })
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
