"""
app/main.py – FastAPI application entrypoint.
Mounts all routers, initializes DB and cache on startup.
"""
import os
import sys

# Get the absolute path of the backend directory (parent of app)
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import get_settings
from app.db.mongodb import connect_db, close_db
from app.services.cache_service import init_cache
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.audit_log import AuditLogMiddleware
from app.routers import shorten, redirect, analytics, health

# ── Logging setup ──────────────────────────────────────────────────────────────
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ── Lifespan (startup / shutdown) ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting URL Shortener API...")
    try:
        await connect_db(settings.mongodb_uri, settings.database_name)
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB during startup: {e}")
    init_cache(
        max_size=settings.cache_max_size,
        ttl_seconds=settings.cache_ttl_seconds,
    )
    logger.info("✅ All services initialized.")
    yield
    logger.info("🛑 Shutting down...")
    await close_db()


# ── App factory ────────────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "A production-grade URL Shortener with analytics, expiry support, "
        "rate limiting, and an agentic SDLC orchestration layer."
    ),
    lifespan=lifespan,
)

# ── Middleware (order matters: outermost first) ────────────────────────────────
app.add_middleware(AuditLogMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=settings.rate_limit_per_minute)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(health.router)
app.include_router(shorten.router)
app.include_router(analytics.router)
app.include_router(redirect.router)   # Must be LAST – catches /{short_code}


# ── Root ───────────────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"])
async def root():
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }


# ── Global exception handler ───────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )
