"""
config.py – Application settings loaded from .env
Uses pydantic-settings for type-safe environment management.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


import os

class Settings(BaseSettings):
    # MongoDB
    mongodb_uri: str = "mongodb+srv://satyam:satyam@cluster0.hudmzzv.mongodb.net/?appName=Cluster0"
    database_name: str = "url-shortener-project-db"

    # App
    base_url: str = "http://localhost:8000"
    short_code_length: int = 7
    app_title: str = "URL Shortener API"
    app_version: str = "1.0.0"

    # Rate limiting (requests per minute per IP)
    rate_limit_per_minute: int = 30

    # Cache
    cache_max_size: int = 1000
    cache_ttl_seconds: int = 300

    # Logging
    log_level: str = "INFO"

    model_config = {
        "extra": "ignore",
    }

    def __init__(self, **values):
        super().__init__(**values)
        # Dynamic fallback for Vercel production deployments
        vercel_url = os.environ.get("VERCEL_URL")
        if vercel_url:
            self.base_url = f"https://{vercel_url}"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
