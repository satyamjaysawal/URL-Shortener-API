"""
tests/unit/test_url_service.py – Unit tests for URL service logic.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ── Short code generation ──────────────────────────────────────────────────────

def test_generate_code_length():
    """Generated code should be exactly the requested length."""
    from app.services.url_service import _generate_code
    code = _generate_code(7)
    assert len(code) == 7


def test_generate_code_alphanumeric():
    """Generated code should only contain alphanumeric characters."""
    from app.services.url_service import _generate_code
    import string
    code = _generate_code(10)
    allowed = set(string.ascii_letters + string.digits)
    assert all(c in allowed for c in code)


def test_generate_code_uniqueness():
    """Generated codes should be unique across many iterations."""
    from app.services.url_service import _generate_code
    codes = {_generate_code(7) for _ in range(1000)}
    # With 62^7 possibilities, collision probability is near zero
    assert len(codes) >= 999


def test_generate_code_custom_length():
    """Short code length should be configurable."""
    from app.services.url_service import _generate_code
    for length in [4, 7, 10, 12]:
        assert len(_generate_code(length)) == length


# ── URL validation ─────────────────────────────────────────────────────────────

def test_url_request_valid():
    """Valid URL should pass validation."""
    from app.models.url import URLRequest
    req = URLRequest(long_url="https://www.example.com/some/path?q=1")
    assert req.long_url == "https://www.example.com/some/path?q=1"


def test_url_request_strips_whitespace():
    """URL validator should strip leading/trailing whitespace."""
    from app.models.url import URLRequest
    req = URLRequest(long_url="  https://example.com  ")
    assert req.long_url == "https://example.com"


def test_url_request_rejects_no_scheme():
    """URL without http/https scheme should be rejected."""
    from app.models.url import URLRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        URLRequest(long_url="www.example.com")


def test_url_request_custom_alias_valid():
    """Valid custom alias should be accepted."""
    from app.models.url import URLRequest
    req = URLRequest(long_url="https://example.com", custom_alias="my-link")
    assert req.custom_alias == "my-link"


def test_url_request_custom_alias_too_short():
    """Custom alias shorter than 3 chars should be rejected."""
    from app.models.url import URLRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        URLRequest(long_url="https://example.com", custom_alias="ab")


def test_url_request_custom_alias_invalid_chars():
    """Custom alias with special characters should be rejected."""
    from app.models.url import URLRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        URLRequest(long_url="https://example.com", custom_alias="my alias!")


def test_url_request_expires_in_hours_valid():
    """Valid expiry should be accepted."""
    from app.models.url import URLRequest
    req = URLRequest(long_url="https://example.com", expires_in_hours=24)
    assert req.expires_in_hours == 24


def test_url_request_expires_in_hours_too_large():
    """Expiry > 8760 hours (1 year) should be rejected."""
    from app.models.url import URLRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        URLRequest(long_url="https://example.com", expires_in_hours=9000)


# ── Cache service ──────────────────────────────────────────────────────────────

def test_cache_set_get():
    """Cache should return the value that was set."""
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=10, ttl_seconds=60)
    cache.set("abc123", {"long_url": "https://example.com"})
    result = cache.get("abc123")
    assert result == {"long_url": "https://example.com"}


def test_cache_miss_returns_none():
    """Cache miss should return None."""
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=10, ttl_seconds=60)
    assert cache.get("nonexistent") is None


def test_cache_delete():
    """Deleted cache entry should return None on next get."""
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=10, ttl_seconds=60)
    cache.set("key1", {"long_url": "https://example.com"})
    cache.delete("key1")
    assert cache.get("key1") is None


def test_cache_eviction():
    """Cache should evict LRU entry when max size exceeded."""
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=3, ttl_seconds=60)
    cache.set("a", {"v": 1})
    cache.set("b", {"v": 2})
    cache.set("c", {"v": 3})
    cache.set("d", {"v": 4})  # Should evict "a" (LRU)
    assert cache.get("a") is None
    assert cache.get("d") == {"v": 4}


def test_cache_ttl_expiry():
    """Cache entry should expire after TTL."""
    import time
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=10, ttl_seconds=1)
    cache.set("key", {"long_url": "https://example.com"})
    assert cache.get("key") is not None
    time.sleep(1.1)
    assert cache.get("key") is None


def test_cache_stats():
    """Cache stats should track hits and misses."""
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=10, ttl_seconds=60)
    cache.set("key", {"v": 1})
    cache.get("key")    # hit
    cache.get("miss")   # miss
    stats = cache.stats
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["hit_rate_pct"] == 50.0
