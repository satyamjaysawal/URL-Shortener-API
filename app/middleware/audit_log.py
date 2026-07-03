"""
middleware/audit_log.py – Request/response audit logging with trace IDs.
Every request is logged with method, path, status, latency, and a trace ID.
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid
import logging
import json

logger = logging.getLogger("audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with a unique trace ID for observability."""

    async def dispatch(self, request: Request, call_next):
        trace_id = str(uuid.uuid4())
        start = time.monotonic()

        # Attach trace ID to request state for downstream use
        request.state.trace_id = trace_id

        response = await call_next(request)
        latency_ms = round((time.monotonic() - start) * 1000, 2)

        log_entry = {
            "trace_id": trace_id,
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }
        logger.info(json.dumps(log_entry))

        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(latency_ms)
        return response
