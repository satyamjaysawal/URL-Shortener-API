"""
models/ai.py – Pydantic models for AI URL analysis.
"""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional


class AIAnalyzeRequest(BaseModel):
    """Request body for AI-powered URL analysis."""
    long_url: str = Field(..., description="The URL to analyze")
    gemini_api_key: Optional[str] = Field(
        None,
        description="Optional user-provided Gemini API key for this session",
    )

    @field_validator("gemini_api_key")
    @classmethod
    def validate_gemini_key(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) < 10:
            raise ValueError("Gemini API key is too short")
        return v

    @field_validator("long_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(v) > 2048:
            raise ValueError("URL too long (max 2048 characters)")
        return v


class AIAnalyzeResponse(BaseModel):
    """AI analysis result for a URL."""
    long_url: str
    category: str
    safety_status: str
    tags: List[str] = []
    suggested_alias: Optional[str] = None
    safe_to_shorten: bool = True
    model: str = "gemini-2.5-flash"