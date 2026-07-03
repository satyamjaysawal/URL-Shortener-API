"""
services/analytics_service.py – Click tracking and aggregation queries.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from collections import defaultdict

from app.db.mongodb import get_db
from app.models.analytics import ClickEvent, AnalyticsSummary, DailyClickStat, TopURL
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def record_click(short_code: str, ip: Optional[str], user_agent: Optional[str], referer: Optional[str]) -> None:
    """Persist a click event to the clicks collection."""
    db = get_db()
    event = {
        "short_code": short_code,
        "timestamp": datetime.now(timezone.utc),
        "ip_address": ip,
        "user_agent": user_agent,
        "referer": referer or "direct",
    }
    await db.clicks.insert_one(event)


async def get_analytics(short_code: str) -> Optional[AnalyticsSummary]:
    """Return full analytics summary for a short URL."""
    db = get_db()
    doc = await db.urls.find_one({"short_code": short_code})
    if not doc:
        return None

    now = datetime.now(timezone.utc)
    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)

    # Fetch all clicks for this code
    clicks_cursor = db.clicks.find({"short_code": short_code})
    all_clicks = await clicks_cursor.to_list(length=10000)

    # Normalize timestamps to timezone-aware UTC
    for c in all_clicks:
        if c["timestamp"].tzinfo is None:
            c["timestamp"] = c["timestamp"].replace(tzinfo=timezone.utc)

    clicks_7 = sum(1 for c in all_clicks if c["timestamp"] >= cutoff_7)
    clicks_30 = sum(1 for c in all_clicks if c["timestamp"] >= cutoff_30)

    # Daily breakdown (last 30 days)
    daily_counts: dict[str, int] = defaultdict(int)
    referer_counts: dict[str, int] = defaultdict(int)
    for click in all_clicks:
        day = click["timestamp"].strftime("%Y-%m-%d")
        daily_counts[day] += 1
        referer_counts[click.get("referer", "direct")] += 1

    daily_breakdown = [
        DailyClickStat(date=day, clicks=count)
        for day, count in sorted(daily_counts.items())
    ]
    top_referers = [
        {"referer": ref, "count": cnt}
        for ref, cnt in sorted(referer_counts.items(), key=lambda x: -x[1])[:5]
    ]

    return AnalyticsSummary(
        short_code=short_code,
        long_url=doc["long_url"],
        total_clicks=doc.get("clicks", 0),
        clicks_last_7_days=clicks_7,
        clicks_last_30_days=clicks_30,
        daily_breakdown=daily_breakdown,
        top_referers=top_referers,
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
        expires_at=doc.get("expires_at"),
        category=doc.get("category"),
        tags=doc.get("tags"),
        safety_status=doc.get("safety_status"),
    )


async def get_top_urls(limit: int = 10) -> List[TopURL]:
    """Return top URLs sorted by click count."""
    db = get_db()
    cursor = db.urls.find({"is_active": True}).sort("clicks", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [
        TopURL(
            short_code=d["short_code"],
            short_url=f"{settings.base_url}/{d['short_code']}",
            long_url=d["long_url"],
            clicks=d.get("clicks", 0),
            created_at=d["created_at"],
        )
        for d in docs
    ]
