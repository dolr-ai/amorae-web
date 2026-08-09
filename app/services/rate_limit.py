"""A small in-memory sliding-window rate limiter.

Guards the chat message endpoint, which is the one route that spends money
(LLM tokens) and — since anonymous web chat — is reachable by anyone. Without
a bound, a single script could run up the OpenRouter bill.

In-memory and per-process: with two replicas an abuser gets at most 2× the
limit, which is an acceptable first guard. A global limit needs Redis (the
Sentinel is already on the cluster); this module is the seam for that — swap
the dict for a Redis INCR+EXPIRE and the callers don't change.

Keyed by client IP, taken from Cloudflare's `CF-Connecting-IP` (all traffic is
CF-routed) so it's the real client, not the edge.
"""

import time
from collections import defaultdict, deque

from fastapi import Request

# key -> deque[timestamps], pruned on read. Bounded by the window, so it can't
# grow without limit for a given key.
_hits: dict[str, deque] = defaultdict(deque)


def client_key(request: Request) -> str:
    cf = request.headers.get("CF-Connecting-IP")
    if cf:
        return cf.strip()
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check(key: str, max_hits: int, window_seconds: int) -> bool:
    """Record a hit and return True if the caller is WITHIN the limit, False if
    it has exceeded it. Prunes timestamps older than the window on each call."""
    now = time.time()
    cutoff = now - window_seconds
    bucket = _hits[key]
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= max_hits:
        return False
    bucket.append(now)
    return True


def reset() -> None:
    """Test hook — clears all counters."""
    _hits.clear()
