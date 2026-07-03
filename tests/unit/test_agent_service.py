"""
tests/unit/test_agent_service.py – Unit tests for LangGraph safety agent and alias suggester.
"""
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_agent_workflow_safe_url(mock_client_class):
    """Workflow should categorize and suggest smart alias for a safe URL."""
    from app.services.agent_service import run_url_agent_workflow

    # Mock response for analyze_url
    mock_response_analysis = MagicMock()
    mock_response_analysis.parsed = MagicMock(
        category="Technology",
        safety_status="safe",
        tags=["programming", "developer"]
    )

    # Mock response for suggest_alias
    mock_response_alias = MagicMock()
    mock_response_alias.parsed = MagicMock(
        suggested_alias="devhub"
    )

    # Setup the mock client
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [mock_response_analysis, mock_response_alias]
    mock_client_class.return_value = mock_client

    res = await run_url_agent_workflow("https://github.com")

    assert res["category"] == "Technology"
    assert res["safety_status"] == "safe"
    assert "programming" in res["tags"]
    assert res["smart_alias"] == "devhub"
    assert res["error"] is None


@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_agent_workflow_unsafe_url(mock_client_class):
    """Workflow should immediately terminate on an unsafe URL and skip alias suggestion."""
    from app.services.agent_service import run_url_agent_workflow

    # Mock response for analyze_url (returns unsafe)
    mock_response_analysis = MagicMock()
    mock_response_analysis.parsed = MagicMock(
        category="Spam",
        safety_status="unsafe",
        tags=["malicious", "phishing"]
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response_analysis
    mock_client_class.return_value = mock_client

    res = await run_url_agent_workflow("https://malicious-spam-url.com")

    assert res["category"] == "Spam"
    assert res["safety_status"] == "unsafe"
    assert res["smart_alias"] is None  # Node suggest_alias should be skipped
    assert res["error"] is None
