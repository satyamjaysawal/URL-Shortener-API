"""
tests/unit/test_ai_router.py – Unit tests for AI analyze endpoint.
"""
import pytest
import sys
import os
from unittest.mock import patch, AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.asyncio
@patch("app.routers.ai.run_url_agent_workflow", new_callable=AsyncMock)
async def test_analyze_safe_url(mock_workflow):
    """Analyze endpoint should return full AI insights for safe URLs."""
    from app.routers.ai import analyze_url
    from app.models.ai import AIAnalyzeRequest

    mock_workflow.return_value = {
        "long_url": "https://github.com",
        "category": "Technology",
        "safety_status": "safe",
        "tags": ["code", "developer"],
        "smart_alias": "ghub",
        "error": None,
    }

    req = AIAnalyzeRequest(long_url="https://github.com")
    res = await analyze_url(req)

    assert res.category == "Technology"
    assert res.safety_status == "safe"
    assert res.suggested_alias == "ghub"
    assert res.safe_to_shorten is True
    assert "code" in res.tags


@pytest.mark.asyncio
@patch("app.routers.ai.run_url_agent_workflow", new_callable=AsyncMock)
async def test_analyze_unsafe_url(mock_workflow):
    """Analyze endpoint should flag unsafe URLs without suggesting alias."""
    from app.routers.ai import analyze_url
    from app.models.ai import AIAnalyzeRequest

    mock_workflow.return_value = {
        "long_url": "https://phishing-site.com",
        "category": "Spam",
        "safety_status": "unsafe",
        "tags": ["phishing"],
        "smart_alias": None,
        "error": None,
    }

    req = AIAnalyzeRequest(long_url="https://phishing-site.com")
    res = await analyze_url(req)

    assert res.safety_status == "unsafe"
    assert res.safe_to_shorten is False
    assert res.suggested_alias is None