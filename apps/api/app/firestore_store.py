"""Firestore persistence for analyses — keyed by user uid.

Optional. When ENABLE_FIRESTORE=1, completed analyses get mirrored to
`users/{uid}/analyses/{analysis_id}`. Anonymous analyses stay in-memory only.
"""
from __future__ import annotations
import logging
import os
from functools import lru_cache
from typing import Optional

log = logging.getLogger("lexguard.firestore")

ENABLE_FIRESTORE = os.getenv("ENABLE_FIRESTORE", "0") == "1"


@lru_cache(maxsize=1)
def _client():
    if not ENABLE_FIRESTORE:
        return None
    try:
        from google.cloud import firestore
        return firestore.Client()
    except Exception as exc:
        log.warning("firestore init failed: %s", exc)
        return None


def save_analysis(uid: str, analysis_id: str, payload: dict) -> bool:
    """Mirror analysis under users/{uid}/analyses/{analysis_id}. Strips bulky fields."""
    db = _client()
    if db is None or not uid:
        return False
    try:
        slim = {
            "id": payload.get("id"),
            "filename": payload.get("filename"),
            "contract_type": payload.get("contract_type"),
            "perspective": payload.get("perspective"),
            "overall_score": payload.get("overall_score"),
            "overall_label": payload.get("overall_label"),
            "stage": payload.get("stage"),
            "clause_count": len(payload.get("clauses", []) or []),
            "created_at": payload.get("created_at"),
            "top_risk_clause_ids": payload.get("top_risk_clause_ids", []),
        }
        db.collection("users").document(uid).collection("analyses").document(analysis_id).set(slim)
        return True
    except Exception as exc:
        log.warning("firestore save failed: %s", exc)
        return False


def list_user_analyses(uid: str, limit: int = 50) -> list[dict]:
    db = _client()
    if db is None or not uid:
        return []
    try:
        from google.cloud import firestore
        q = (db.collection("users").document(uid).collection("analyses")
             .order_by("created_at", direction=firestore.Query.DESCENDING)
             .limit(limit))
        return [d.to_dict() for d in q.stream()]
    except Exception as exc:
        log.warning("firestore list failed: %s", exc)
        return []


def delete_user_analysis(uid: str, analysis_id: str) -> bool:
    db = _client()
    if db is None or not uid:
        return False
    try:
        db.collection("users").document(uid).collection("analyses").document(analysis_id).delete()
        return True
    except Exception as exc:
        log.warning("firestore delete failed: %s", exc)
        return False
