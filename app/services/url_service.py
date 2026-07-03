"""
services/url_service.py – Core URL business logic.
Handles short code generation, collision avoidance, custom aliases, expiry.
"""
import secrets
import string
import logging
from typing import Optional
from datetime import datetime, timezone, timedelta

from app.db.mongodb import get_db
from app.services.cache_service import get_cache
from app.models.url import URLRequest, URLResponse, URLDocument, URLStats
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

ALPHABET = string.ascii_letters + string.digits


def _generate_code(length: int = 7) -> str:
    """Generate a random alphanumeric short code."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


async def create_short_url(request: URLRequest) -> URLResponse:
    """
    Create a new short URL entry in MongoDB.
    Supports custom alias and expiry.
    """
    db = get_db()

    # Determine short code
    if request.custom_alias:
        code = request.custom_alias
        existing = await db.urls.find_one({"short_code": code})
        if existing:
            raise ValueError(f"Alias '{code}' is already taken.")
    else:
        # Generate unique code with collision avoidance (max 5 attempts)
        for attempt in range(5):
            code = _generate_code(settings.short_code_length)
            if not await db.urls.find_one({"short_code": code}):
                break
        else:
            raise RuntimeError("Failed to generate a unique short code. Please try again.")

    now = datetime.now(timezone.utc)
    expires_at: Optional[datetime] = None
    if request.expires_in_hours:
        expires_at = now + timedelta(hours=request.expires_in_hours)

    doc = {
        "short_code": code,
        "long_url": request.long_url,
        "clicks": 0,
        "is_active": True,
        "created_at": now,
        "expires_at": expires_at,
    }
    await db.urls.insert_one(doc)
    logger.info(f"Created short URL: {code} -> {request.long_url[:60]}")

    return URLResponse(
        short_url=f"{settings.base_url}/{code}",
        short_code=code,
        long_url=request.long_url,
        created_at=now,
        expires_at=expires_at,
    )


async def resolve_url(short_code: str) -> Optional[str]:
    """
    Resolve a short code to its long URL.
    Returns None if not found, inactive, or expired.
    Uses cache-first lookup.
    """
    cache = get_cache()
    cached = cache.get(short_code)
    if cached:
        return cached.get("long_url")

    db = get_db()
    doc = await db.urls.find_one({"short_code": short_code})
    if not doc:
        return None
    if not doc.get("is_active", True):
        return None
    expires_at = doc.get("expires_at")
    if expires_at:
        # MongoDB returns timezone-naive datetimes – normalize to UTC-aware
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < datetime.now(timezone.utc):
            return None

    # Cache the result
    cache.set(short_code, {"long_url": doc["long_url"]})
    return doc["long_url"]


async def increment_clicks(short_code: str) -> None:
    """Atomically increment click counter."""
    db = get_db()
    await db.urls.update_one({"short_code": short_code}, {"$inc": {"clicks": 1}})


async def get_url_stats(short_code: str) -> Optional[URLStats]:
    """Return stats for a short URL."""
    db = get_db()
    doc = await db.urls.find_one({"short_code": short_code})
    if not doc:
        return None
    return URLStats(
        short_code=doc["short_code"],
        long_url=doc["long_url"],
        clicks=doc.get("clicks", 0),
        is_active=doc.get("is_active", True),
        created_at=doc["created_at"],
        expires_at=doc.get("expires_at"),
        short_url=f"{settings.base_url}/{doc['short_code']}",
    )


async def deactivate_url(short_code: str) -> bool:
    """Soft-delete a short URL by marking it inactive."""
    db = get_db()
    result = await db.urls.update_one(
        {"short_code": short_code},
        {"$set": {"is_active": False}}
    )
    if result.modified_count > 0:
        get_cache().delete(short_code)
        logger.info(f"Deactivated short URL: {short_code}")
        return True
    return False
