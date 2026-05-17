"""Simple in-memory token bucket per IP. Prevents demo-day cost runaway."""
from __future__ import annotations
import time
from collections import defaultdict
from fastapi import Request, HTTPException


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


# 10 analyses per 10 min per IP; 30 chat msgs per 5 min per IP
analyze_bucket = TokenBucket(capacity=10, refill_per_sec=10 / 600)
chat_bucket = TokenBucket(capacity=30, refill_per_sec=30 / 300)


def _client_ip(req: Request) -> str:
    fwd = req.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return req.client.host if req.client else "unknown"


def limit_analyze(req: Request) -> None:
    if not analyze_bucket.consume(_client_ip(req)):
        raise HTTPException(status_code=429, detail="Too many analyses. Wait a minute.")


def limit_chat(req: Request) -> None:
    if not chat_bucket.consume(_client_ip(req)):
        raise HTTPException(status_code=429, detail="Too many chat messages. Slow down.")
