"""Firebase Auth — optional ID token verification.

If the request carries `Authorization: Bearer <id_token>` and Firebase Admin
is initialized, we verify the token and return the decoded claims (uid, email).
If absent or invalid, returns None — endpoints stay open for anonymous demo.
"""
from __future__ import annotations
import logging
import os
from functools import lru_cache
from typing import Optional

from fastapi import Header

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
            # Uses GOOGLE_APPLICATION_CREDENTIALS automatically
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)
        return True
    except Exception as exc:
        log.warning("firebase init failed: %s", exc)
        return False


async def current_user(
    authorization: Optional[str] = Header(default=None),
) -> Optional[dict]:
    """Optional dep: returns {uid, email} if valid token, else None."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    if not _init_firebase():
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        from firebase_admin import auth as fb_auth
        decoded = fb_auth.verify_id_token(token)
        return {"uid": decoded["uid"], "email": decoded.get("email", "")}
    except Exception as exc:
        log.info("token verify failed: %s", exc)
        return None
