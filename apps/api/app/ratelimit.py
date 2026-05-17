"""Token-bucket rate limit per uid (preferred) or client IP.

XFF handling:
- Only trusted when TRUST_PROXY=1 (set in Cloud Run / behind known LB).
- When trusted, take the RIGHTMOST entry (last proxy hop) — leftmost is
  client-controlled and trivially spoofable.
- When not trusted, ignore XFF entirely and use the socket peer.
"""
from __future__ import annotations
import os
import time
from collections import defaultdict
from fastapi import Request, HTTPException

TRUST_PROXY = os.getenv("TRUST_PROXY", "0") == "1"


class TokenBucket:
    def __init__(self, capacity: int, refill_per_sec: float):
        self.capacity = capacity
        self.refill = refill_per_sec
        self._state: dict[str, tuple[float, float]] = defaultdict(lambda: (capacity, time.time()))

    def consume(self, key: str, cost: float = 1.0) -> bool:
        tokens, last = self._state[key]
        now = time.time()
        tokens = min(self.capacity, tokens + (now - last) * self.refill)
        if tokens < cost:
            self._state[key] = (tokens, now)
            return False
        tokens -= cost
        self._state[key] = (tokens, now)
        return True


analyze_bucket = TokenBucket(capacity=10, refill_per_sec=10 / 600)
chat_bucket = TokenBucket(capacity=30, refill_per_sec=30 / 300)
# tighter per-uid caps once authenticated (Gemini cost guardrail)
analyze_user_bucket = TokenBucket(capacity=20, refill_per_sec=20 / 600)
chat_user_bucket = TokenBucket(capacity=60, refill_per_sec=60 / 300)


def _client_ip(req: Request) -> str:
    if TRUST_PROXY:
        fwd = req.headers.get("x-forwarded-for")
        if fwd:
            # rightmost = last proxy hop (the one we trust); reject empty
            parts = [p.strip() for p in fwd.split(",") if p.strip()]
            if parts:
                return parts[-1]
    return req.client.host if req.client else "unknown"


def _key(req: Request, user: dict | None) -> str:
    if user and user.get("uid"):
        return f"uid:{user['uid']}"
    return f"ip:{_client_ip(req)}"


def limit_analyze(req: Request, user: dict | None = None) -> None:
    key = _key(req, user)
    bucket = analyze_user_bucket if key.startswith("uid:") else analyze_bucket
    if not bucket.consume(key):
        raise HTTPException(status_code=429, detail="Too many analyses. Wait a minute.")


def limit_chat(req: Request, user: dict | None = None) -> None:
    key = _key(req, user)
    bucket = chat_user_bucket if key.startswith("uid:") else chat_bucket
    if not bucket.consume(key):
        raise HTTPException(status_code=429, detail="Too many chat messages. Slow down.")
