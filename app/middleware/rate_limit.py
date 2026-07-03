"""
middleware/rate_limit.py – Sliding-window rate limiter per IP.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from collections import defaultdict, deque
import time
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter.
    Default: 30 requests per 60 seconds per IP.
    Exempts the /health and /docs endpoints.
    """

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, requests_per_minute: int = 30):
        super().__init__(app)
        self._limit = requests_per_minute
        self._window = 60  # seconds
        # ip -> deque of timestamps
        self._windows: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._windows[ip]

        # Remove timestamps outside the sliding window
        while window and now - window[0] > self._window:
            window.popleft()

        if len(window) >= self._limit:
            logger.warning(f"Rate limit exceeded for IP: {ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too many requests",
                    "detail": f"Limit is {self._limit} requests per minute.",
                    "retry_after_seconds": int(self._window - (now - window[0])),
                },
            )

        window.append(now)
        return await call_next(request)
