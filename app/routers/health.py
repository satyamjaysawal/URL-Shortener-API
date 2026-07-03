"""
routers/health.py – GET /health and GET /metrics
"""
from fastapi import APIRouter
from app.db.mongodb import get_db
from app.services.cache_service import get_cache
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])

_start_time = time.time()


@router.get(
    "/health",
    summary="Health check",
    description="Returns application health status including DB connectivity.",
)
async def health_check():
    """Ping MongoDB and return service health."""
    db_status = "healthy"
    try:
        db = get_db()
        await db.client.admin.command("ping")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    uptime_seconds = round(time.time() - _start_time, 1)
    return {
        "status": "ok" if db_status == "healthy" else "degraded",
        "database": db_status,
        "uptime_seconds": uptime_seconds,
        "version": "1.0.0",
    }


@router.get(
    "/metrics",
    summary="Service metrics",
    description="Returns cache statistics and basic reliability metrics.",
)
async def get_metrics():
    """Return cache hit rates and service metrics."""
    try:
        cache_stats = get_cache().stats
    except Exception:
        cache_stats = {}

    uptime_seconds = round(time.time() - _start_time, 1)
    return {
        "uptime_seconds": uptime_seconds,
        "cache": cache_stats,
    }
