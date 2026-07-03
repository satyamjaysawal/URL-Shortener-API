"""
routers/analytics.py – GET /stats/{short_code} and GET /analytics/top
"""
from fastapi import APIRouter, HTTPException, Query, status
from app.models.analytics import AnalyticsSummary, TopURL
from app.models.url import URLStats
from app.services import url_service, analytics_service
from typing import List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/stats/{short_code}",
    response_model=URLStats,
    summary="Basic stats for a short URL",
    description="Returns click count, active status, and expiry for a short URL.",
)
async def get_stats(short_code: str):
    stats = await url_service.get_url_stats(short_code)
    if stats is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found.")
    return stats


@router.get(
    "/detail/{short_code}",
    response_model=AnalyticsSummary,
    summary="Detailed analytics for a short URL",
    description="Returns full click breakdown: daily stats, top referers, 7-day/30-day counts.",
)
async def get_detailed_analytics(short_code: str):
    summary = await analytics_service.get_analytics(short_code)
    if summary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found.")
    return summary


@router.get(
    "/top",
    response_model=List[TopURL],
    summary="Top URLs by click count",
    description="Returns the most-clicked active short URLs.",
)
async def get_top_urls(
    limit: int = Query(default=10, ge=1, le=100, description="Number of top URLs to return")
):
    return await analytics_service.get_top_urls(limit=limit)
