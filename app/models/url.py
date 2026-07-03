"""
models/url.py – Pydantic models for URL entities.
"""
from pydantic import BaseModel, HttpUrl, Field, field_validator
from typing import Optional
from datetime import datetime, timezone


class URLRequest(BaseModel):
    """Request body for creating a short URL."""
    long_url: str = Field(..., description="The original long URL to shorten")
    custom_alias: Optional[str] = Field(
        None,
        min_length=3,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Optional custom short code alias"
    )
    expires_in_hours: Optional[int] = Field(
        None,
        ge=1,
        le=8760,
        description="Hours until the short URL expires (max 365 days)"
    )

    @field_validator("long_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()  # strip first, then validate
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        return v


class URLResponse(BaseModel):
    """Response body after creating a short URL."""
    short_url: str
    short_code: str
    long_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class URLDocument(BaseModel):
    """Internal MongoDB document shape."""
    short_code: str
    long_url: str
    clicks: int = 0
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    model_config = {"arbitrary_types_allowed": True}


class URLStats(BaseModel):
    """Statistics for a short URL."""
    short_code: str
    long_url: str
    clicks: int
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime] = None
    short_url: str
