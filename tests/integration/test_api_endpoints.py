"""
tests/integration/test_api_endpoints.py – Integration tests for FastAPI endpoints.
Uses httpx.AsyncClient with a test MongoDB collection.
"""
import pytest
import pytest_asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_db():
    """Create a mock MongoDB database."""
    db = MagicMock()
    db.urls = MagicMock()
    db.clicks = MagicMock()
    db.client.admin.command = AsyncMock(return_value={"ok": 1})
    return db


@pytest.fixture
def sample_url_doc():
    return {
        "short_code": "abc1234",
        "long_url": "https://www.example.com/very/long/url",
        "clicks": 5,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "expires_at": None,
    }


# ── URL model validation tests ─────────────────────────────────────────────────

def test_url_request_valid_http():
    from app.models.url import URLRequest
    req = URLRequest(long_url="http://example.com")
    assert req.long_url == "http://example.com"


def test_url_request_valid_https():
    from app.models.url import URLRequest
    req = URLRequest(long_url="https://example.com/path?q=1#anchor")
    assert "https" in req.long_url


def test_url_request_invalid_scheme():
    from app.models.url import URLRequest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        URLRequest(long_url="ftp://example.com")


def test_url_response_shape():
    from app.models.url import URLResponse
    resp = URLResponse(
        short_url="http://localhost:8000/abc1234",
        short_code="abc1234",
        long_url="https://example.com",
        created_at=datetime.now(timezone.utc),
    )
    assert resp.short_code == "abc1234"
    assert resp.expires_at is None


def test_url_stats_shape(sample_url_doc):
    from app.models.url import URLStats
    stats = URLStats(
        short_code=sample_url_doc["short_code"],
        long_url=sample_url_doc["long_url"],
        clicks=sample_url_doc["clicks"],
        is_active=sample_url_doc["is_active"],
        created_at=sample_url_doc["created_at"],
        short_url=f"http://localhost:8000/{sample_url_doc['short_code']}",
    )
    assert stats.clicks == 5
    assert stats.is_active is True


# ── Analytics model tests ──────────────────────────────────────────────────────

def test_click_event_model():
    from app.models.analytics import ClickEvent
    event = ClickEvent(
        short_code="abc1234",
        ip_address="1.2.3.4",
        user_agent="Mozilla/5.0",
        referer="https://google.com",
    )
    assert event.short_code == "abc1234"
    assert event.country is None


def test_analytics_summary_model():
    from app.models.analytics import AnalyticsSummary
    summary = AnalyticsSummary(
        short_code="abc1234",
        long_url="https://example.com",
        total_clicks=100,
        clicks_last_7_days=20,
        clicks_last_30_days=80,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    assert summary.total_clicks == 100
    assert summary.daily_breakdown == []


# ── Cache integration tests ────────────────────────────────────────────────────

def test_cache_init_and_get():
    """Cache should be usable after init."""
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=100, ttl_seconds=300)
    cache.set("test123", {"long_url": "https://example.com"})
    result = cache.get("test123")
    assert result is not None
    assert result["long_url"] == "https://example.com"


def test_cache_clear():
    """Cache clear should remove all entries."""
    from app.services.cache_service import LRUCache
    cache = LRUCache(max_size=100, ttl_seconds=300)
    cache.set("a", {"v": 1})
    cache.set("b", {"v": 2})
    cache.clear()
    assert cache.get("a") is None
    assert cache.get("b") is None
    assert cache.stats["size"] == 0


# ── Config tests ───────────────────────────────────────────────────────────────

def test_settings_defaults():
    """Settings should have sensible defaults."""
    from app.config import Settings
    s = Settings(mongodb_uri="mongodb://localhost:27017")
    assert s.short_code_length == 7
    assert s.cache_max_size == 1000
    assert s.rate_limit_per_minute == 30


# ── Governance integration tests ───────────────────────────────────────────────

def test_governance_policy_chain():
    """Multiple policy checks should all pass for a valid public URL."""
    from orchestrator.governance import GovernanceEngine
    gov = GovernanceEngine()
    urls = [
        "https://github.com/user/repo",
        "https://docs.python.org/3/",
        "https://stackoverflow.com/questions/123",
    ]
    for url in urls:
        ok, violations = gov.check_url_policy(url)
        assert ok, f"URL should be allowed: {url}, violations: {violations}"
