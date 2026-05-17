"""Token bucket rate-limit tests."""
import time
from app.ratelimit import TokenBucket


def test_bucket_starts_full():
    b = TokenBucket(capacity=5, refill_per_sec=1)
    for _ in range(5):
        assert b.consume("ip-1") is True
    assert b.consume("ip-1") is False


def test_bucket_refills_over_time():
    b = TokenBucket(capacity=2, refill_per_sec=100)
    assert b.consume("ip-1") is True
    assert b.consume("ip-1") is True
    assert b.consume("ip-1") is False
    time.sleep(0.05)
    assert b.consume("ip-1") is True


def test_buckets_independent_per_key():
    b = TokenBucket(capacity=1, refill_per_sec=0.001)
    assert b.consume("ip-a") is True
    assert b.consume("ip-b") is True
    assert b.consume("ip-a") is False
