"""
models/analytics.py – Pydantic models for analytics and click events.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone


class ClickEvent(BaseModel):
    """A single click event recorded on redirect."""
    short_code: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    country: Optional[str] = None  # Reserved for future geo-lookup


class DailyClickStat(BaseModel):
    """Aggregated click count for a single day."""
    date: str          # ISO date string YYYY-MM-DD
    clicks: int


class AnalyticsSummary(BaseModel):
    """Full analytics summary for a short URL."""
    short_code: str
    long_url: str
    total_clicks: int
    clicks_last_7_days: int
    clicks_last_30_days: int
    daily_breakdown: List[DailyClickStat] = []
    top_referers: List[dict] = []
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    safety_status: Optional[str] = None


class TopURL(BaseModel):
    """Entry in the top URLs leaderboard."""
    short_code: str
    short_url: str
    long_url: str
    clicks: int
    created_at: datetime
