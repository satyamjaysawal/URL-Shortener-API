"""
config.py – Application settings loaded from .env
Uses pydantic-settings for type-safe environment management.
"""
import os
from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MongoDB – accepts MONGODB_URI or Vercel's DATABASE_URL
    mongodb_uri: str = Field(
        default="mongodb+srv://satyam:satyam@cluster0.hudmzzv.mongodb.net/?appName=Cluster0",
        validation_alias=AliasChoices("MONGODB_URI", "DATABASE_URL", "mongodb_uri"),
    )
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

    # Google GenAI / Gemini
    google_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "google_api_key"),
    )
    gemini_flash_model: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("GEMINI_FLASH_MODEL", "gemini_flash_model"),
    )

    def model_post_init(self, __context) -> None:
        # On Vercel, prefer a valid Atlas integration DATABASE_URL when present
        if os.environ.get("VERCEL"):
            database_url = (os.environ.get("DATABASE_URL") or "").strip()
            if database_url.startswith(("mongodb://", "mongodb+srv://")):
                self.mongodb_uri = database_url

        vercel_url = os.environ.get("VERCEL_URL")
        if vercel_url:
            self.base_url = f"https://{vercel_url}"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()
