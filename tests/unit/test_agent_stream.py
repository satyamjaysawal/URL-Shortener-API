"""
tests/unit/test_agent_stream.py – Unit tests for LangGraph SSE streaming.
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_stream_emits_workflow_events(mock_client_class):
    """Stream should emit LangGraph node events in order."""
    from app.services.agent_service import stream_url_agent_workflow

    mock_response_analysis = MagicMock()
    mock_response_analysis.parsed = MagicMock(
        category="Technology",
        safety_status="safe",
        tags=["code"],
    )
    mock_response_alias = MagicMock()
    mock_response_alias.parsed = MagicMock(suggested_alias="devhub")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [mock_response_analysis, mock_response_alias]
    mock_client_class.return_value = mock_client

    events = [e async for e in stream_url_agent_workflow("https://github.com")]
    event_types = [e["event"] for e in events]

    assert "workflow_start" in event_types
    assert "node_start" in event_types
    assert "node_complete" in event_types
    assert "governance_decision" in event_types
    assert "workflow_complete" in event_types

    complete = next(e for e in events if e["event"] == "workflow_complete")
    assert complete["result"]["category"] == "Technology"
    assert complete["result"]["suggested_alias"] == "devhub"


@pytest.mark.asyncio
@patch("google.genai.Client")
async def test_stream_blocks_unsafe_url(mock_client_class):
    """Unsafe URLs should skip alias node and block at end."""
    from app.services.agent_service import stream_url_agent_workflow

    mock_response = MagicMock()
    mock_response.parsed = MagicMock(
        category="Spam",
        safety_status="unsafe",
        tags=["phishing"],
    )
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    events = [e async for e in stream_url_agent_workflow("https://evil-phish.com")]
    skipped = [e for e in events if e.get("event") == "node_skipped"]
    complete = next(e for e in events if e["event"] == "workflow_complete")

    assert any(s["node"] == "suggest_alias" for s in skipped)
    assert complete["result"]["safe_to_shorten"] is False