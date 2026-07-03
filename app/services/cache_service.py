"""
services/cache_service.py – In-memory LRU cache for hot URL lookups.
Avoids redundant DB reads for frequently accessed short codes.
"""
from collections import OrderedDict
from typing import Optional
import time
import threading
import logging

logger = logging.getLogger(__name__)


class LRUCache:
    """Thread-safe LRU cache with TTL support."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 300):
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # key -> (value, expires_at)
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[dict]:
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            value, expires_at = self._cache[key]
            if time.monotonic() > expires_at:
                del self._cache[key]
                self._misses += 1
                return None
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: dict) -> None:
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (value, time.monotonic() + self._ttl)
            if len(self._cache) > self._max_size:
                evicted = self._cache.popitem(last=False)
                logger.debug(f"Cache evicted: {evicted[0]}")

    def delete(self, key: str) -> None:
        with self._lock:
            self._cache.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()

    @property
    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_pct": round(hit_rate, 2),
            }


# Module-level singleton
_url_cache: Optional[LRUCache] = None


def init_cache(max_size: int = 1000, ttl_seconds: int = 300) -> None:
    global _url_cache
    _url_cache = LRUCache(max_size=max_size, ttl_seconds=ttl_seconds)
    logger.info(f"✅ Cache initialized (max_size={max_size}, ttl={ttl_seconds}s)")


def get_cache() -> LRUCache:
    global _url_cache
    if _url_cache is None:
        # Auto-initialize fallback for Serverless environments where lifespan startup is skipped
        init_cache()
    return _url_cache
