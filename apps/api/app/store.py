from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any
import time
import numpy as np


class Clause(BaseModel):
    id: str
    type: str
    text: str
    normalized_text: str = ""
    source_offset_start: int = 0
    source_offset_end: int = 0
    page_number: int = 1
    risk_score: float = 0.0
    risk_label: str = "Low"
    risk_components: dict[str, float] = Field(default_factory=dict)
    top_reasons: list[str] = Field(default_factory=list)
    affected_interest: str = "financial"
    plain_explanation: str = ""
    real_world_scenario: str = ""
    suggested_redline: str = ""
    benchmark_diff: dict[str, Any] | None = None


class Chunk(BaseModel):
    id: str
    text: str
    page_number: int = 1
    offset_start: int = 0
    offset_end: int = 0


class ChatMessage(BaseModel):
    role: str
    content: str
    citations: list[str] = Field(default_factory=list)


class Analysis(BaseModel):
    id: str
    filename: str
    contract_type: str
    perspective: str
    stage: str = "queued"
    overall_score: float = 0.0
    overall_label: str = "Low"
    top_risk_clause_ids: list[str] = Field(default_factory=list)
    clauses: list[Clause] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    messages: list[ChatMessage] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    error_message: str | None = None
    created_at: float = Field(default_factory=time.time)

    class Config:
        arbitrary_types_allowed = True


# in-memory state — wiped on process restart, by design
ANALYSES: dict[str, Analysis] = {}
EMBEDDINGS: dict[str, np.ndarray] = {}  # analysis_id -> (N, dim) float32
DEDUPE: dict[str, str] = {}  # sha256 -> analysis_id

TTL_SECONDS = 60 * 60


def evict_stale() -> None:
    now = time.time()
    stale = [aid for aid, a in ANALYSES.items() if now - a.created_at > TTL_SECONDS]
    for aid in stale:
        ANALYSES.pop(aid, None)
        EMBEDDINGS.pop(aid, None)
    # also prune dedupe entries pointing at evicted analyses
    for h, aid in list(DEDUPE.items()):
        if aid not in ANALYSES:
            DEDUPE.pop(h, None)
