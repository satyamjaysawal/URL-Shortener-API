"""
routers/redirect.py – GET /{short_code} redirect with click tracking.
"""
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from app.services import url_service, analytics_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Redirect"])


@router.get(
    "/{short_code}",
    summary="Redirect to original URL",
    description="Redirects to the original long URL and records the click event.",
    response_class=RedirectResponse,
)
async def redirect(short_code: str, request: Request):
    """
    Resolve a short code and redirect (HTTP 302) to the long URL.
    Records IP, user agent, and referer for analytics.
    """
    long_url = await url_service.resolve_url(short_code)
    if long_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Short URL '{short_code}' not found, expired, or inactive.",
        )

    # Record analytics asynchronously (fire-and-forget style)
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    referer = request.headers.get("referer")

    # Increment click counter and record event
    await url_service.increment_clicks(short_code)
    await analytics_service.record_click(short_code, ip, user_agent, referer)

    logger.info(f"Redirected {short_code} -> {long_url[:60]}")
    return RedirectResponse(url=long_url, status_code=status.HTTP_302_FOUND)
