"""In-memory rate limiting middleware (single-process deployments)."""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.core.config import settings
from app.core.errors import DomainError


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window request limiter keyed by client address.

    The WebSocket upgrade and the documentation endpoints are exempt so a
    plant HMI polling loop cannot starve the simulation channels.
    """

    EXEMPT_PREFIXES = ("/docs", "/openapi.json", "/redoc", "/api/health", "/ws/")

    def __init__(self, app, limit_per_minute: int | None = None) -> None:
        super().__init__(app)
        self.limit = limit_per_minute or settings.rate_limit_per_minute
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._hits[client]
        while window and now - window[0] > 60.0:
            window.popleft()
        if len(window) >= self.limit:
            error = DomainError("rate_limited", status_code=429)
            return JSONResponse(
                status_code=429,
                content={"detail": error.to_payload()},
                headers={"Retry-After": "60"},
            )
        window.append(now)
        return await call_next(request)
