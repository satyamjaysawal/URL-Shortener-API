"""
routers/shorten.py – POST /shorten and DELETE /api/urls/{short_code}
"""
from fastapi import APIRouter, HTTPException, status
from app.models.url import URLRequest, URLResponse
from app.services import url_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["URL Shortener"])


@router.post(
    "/shorten",
    response_model=URLResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Shorten a URL",
    description="Create a short URL with an optional custom alias and expiry.",
)
async def shorten_url(request: URLRequest):
    """
    Create a new short URL.

    - **long_url**: The original URL (must start with http:// or https://)
    - **custom_alias**: Optional custom short code (3-30 alphanumeric chars)
    - **expires_in_hours**: Optional TTL in hours (1–8760)
    """
    try:
        return await url_service.create_short_url(request)
    except ValueError as e:
        msg = str(e)
        if "unsafe" in msg.lower():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=msg)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
    except RuntimeError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete(
    "/api/urls/{short_code}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a short URL",
    description="Soft-delete a short URL by marking it inactive. The record is retained for audit purposes.",
)
async def deactivate_url(short_code: str):
    """Soft-delete a short URL."""
    success = await url_service.deactivate_url(short_code)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found.")
    return {"message": f"Short URL '{short_code}' has been deactivated.", "short_code": short_code}
