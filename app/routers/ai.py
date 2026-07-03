"""
routers/ai.py – AI-powered URL analysis endpoints.
"""
import json
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from app.models.ai import AIAnalyzeRequest, AIAnalyzeResponse
from app.services.agent_service import run_url_agent_workflow, stream_url_agent_workflow
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI"])
settings = get_settings()


def _to_response(agent_res: dict, long_url: str) -> AIAnalyzeResponse:
    safety = agent_res.get("safety_status", "safe")
    return AIAnalyzeResponse(
        long_url=long_url,
        category=agent_res.get("category", "Unknown"),
        safety_status=safety,
        tags=agent_res.get("tags", []),
        suggested_alias=agent_res.get("smart_alias"),
        safe_to_shorten=safety != "unsafe",
        model=settings.gemini_flash_model,
    )


@router.post(
    "/ai/analyze",
    response_model=AIAnalyzeResponse,
    summary="Analyze a URL with AI",
    description=(
        "Run Gemini-powered safety check, categorization, tag extraction, "
        "and smart alias suggestion without creating a short URL."
    ),
)
async def analyze_url(request: AIAnalyzeRequest):
    """Analyze a URL using the LangGraph AI agent workflow."""
    try:
        agent_res = await run_url_agent_workflow(
            request.long_url,
            gemini_api_key=request.gemini_api_key,
        )
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI analysis service is temporarily unavailable.",
        )
    return _to_response(agent_res, request.long_url)


@router.post(
    "/ai/analyze/stream",
    summary="Stream LangGraph agent workflow (SSE)",
    description=(
        "Server-Sent Events stream of the LangGraph agent execution. "
        "Emits node_start, node_complete, governance_decision, and workflow_complete events."
    ),
)
async def analyze_url_stream(request: AIAnalyzeRequest):
    """Stream URL analysis via LangGraph with real-time agentic flow events."""

    async def event_generator():
        try:
            async for event in stream_url_agent_workflow(
                request.long_url,
                gemini_api_key=request.gemini_api_key,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            logger.error(f"AI stream failed: {e}")
            err = {"event": "error", "message": "AI analysis stream failed", "detail": str(e)}
            yield f"data: {json.dumps(err)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )