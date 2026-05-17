"""Firebase Auth — ID token verification.

Two deps:
- `current_user`: optional. Returns claims if token valid; None if no header.
  When ENABLE_FIREBASE=1 a bad/expired token raises 401 (fail-closed).
- `require_user`: required. 401 if anonymous when ENABLE_FIREBASE=1.

When ENABLE_FIREBASE=0 both return None (legacy demo mode).
"""
from __future__ import annotations
import logging
import os
from functools import lru_cache
from typing import Optional

from fastapi import Header, HTTPException

log = logging.getLogger("lexguard.auth")

ENABLE_FIREBASE = os.getenv("ENABLE_FIREBASE", "0") == "1"


@lru_cache(maxsize=1)
def _init_firebase() -> bool:
    if not ENABLE_FIREBASE:
        return False
    try:
        import firebase_admin
        from firebase_admin import credentials

        if not firebase_admin._apps:
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        return True
    except Exception as exc:
        log.warning("firebase init failed: %s", exc)
        return False


def _verify(token: str) -> dict:
    from firebase_admin import auth as fb_auth
    decoded = fb_auth.verify_id_token(token)
    return {"uid": decoded["uid"], "email": decoded.get("email", "")}


async def current_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """Optional dep.

    - No Authorization header → None (anonymous allowed by caller).
    - Header present + ENABLE_FIREBASE=1: must verify, else 401.
    - ENABLE_FIREBASE=0: always None (legacy mode).
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    if not ENABLE_FIREBASE:
        return None
    if not _init_firebase():
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return _verify(token)
    except Exception as exc:
        log.info("token verify failed: %s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="Invalid or expired token")


async def require_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """Required dep when ENABLE_FIREBASE=1. Returns None when auth disabled."""
    if not ENABLE_FIREBASE:
        return None  # legacy demo mode
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in required")
    if not _init_firebase():
        raise HTTPException(status_code=503, detail="Auth service unavailable")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return _verify(token)
    except Exception as exc:
        log.info("token verify failed: %s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="Invalid or expired token")
