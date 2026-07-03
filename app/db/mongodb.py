"""
db/mongodb.py – Async MongoDB connection manager with retry logic.
"""
import asyncio
import logging
import os
from typing import Optional

import certifi
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.server_api import ServerApi

logger = logging.getLogger(__name__)

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def _client_options() -> dict:
    """Motor client options tuned for Atlas + serverless (Vercel)."""
    opts = {
        "server_api": ServerApi("1"),
        "serverSelectionTimeoutMS": 10000,
        "connectTimeoutMS": 10000,
        "tlsCAFile": certifi.where(),
        "tlsDisableOCSPEndpointCheck": True,
        "retryWrites": True,
    }
    # Smaller pool for serverless cold starts
    if os.environ.get("VERCEL"):
        opts["maxPoolSize"] = 10
        opts["minPoolSize"] = 0
    return opts


async def connect_db(uri: str, db_name: str, max_retries: int = 3) -> None:
    """Connect to MongoDB with exponential backoff retry."""
    global _client, _db
    for attempt in range(1, max_retries + 1):
        try:
            _client = AsyncIOMotorClient(uri, **_client_options())
            # Trigger actual connection test
            await _client.admin.command("ping")
            _db = _client[db_name]
            # Create indexes
            await _db.urls.create_index("short_code", unique=True)
            await _db.clicks.create_index("short_code")
            await _db.clicks.create_index("timestamp")
            logger.info(f"✅ Connected to MongoDB: {db_name}")
            return
        except Exception as e:
            print(f"DB_CONNECT_ERROR: {e}")
            logger.warning(f"MongoDB connection attempt {attempt}/{max_retries} failed: {e}")
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
            else:
                raise RuntimeError(f"Failed to connect to MongoDB after {max_retries} attempts") from e


async def close_db() -> None:
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")


def get_db() -> AsyncIOMotorDatabase:
    """Return the active database instance."""
    global _db, _client
    if _db is None:
        from app.config import get_settings
        import asyncio
        settings = get_settings()
        # Initialize connection synchronously for this request scope
        _client = AsyncIOMotorClient(settings.mongodb_uri, **_client_options())
        _db = _client[settings.database_name]
    return _db
