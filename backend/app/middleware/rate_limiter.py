# backend/app/middleware/rate_limiter.py
"""
Simple in-memory rate limiter.
Limits pipeline runs and API calls per session.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """In-memory rate limiter with per-session tracking."""

    def __init__(
        self,
        max_pipeline_runs_per_hour: int = 10,
        max_api_calls_per_minute: int = 60,
    ):
        self.max_pipeline_runs = max_pipeline_runs_per_hour
        self.max_api_calls = max_api_calls_per_minute

        # Track: session_id -> list of timestamps
        self._pipeline_runs: dict = defaultdict(list)
        self._api_calls: dict = defaultdict(list)

    def _clean_old_entries(self, entries: list, window: timedelta):
        """Remove entries older than the window."""
        cutoff = datetime.utcnow() - window
        return [t for t in entries if t > cutoff]

    def check_pipeline_rate(self, session_id: str) -> bool:
        """Check if a session can run another pipeline. Returns True if allowed."""
        window = timedelta(hours=1)
        self._pipeline_runs[session_id] = self._clean_old_entries(
            self._pipeline_runs[session_id], window
        )

        if len(self._pipeline_runs[session_id]) >= self.max_pipeline_runs:
            return False

        self._pipeline_runs[session_id].append(datetime.utcnow())
        return True

    def check_api_rate(self, client_id: str) -> bool:
        """Check if a client can make another API call. Returns True if allowed."""
        window = timedelta(minutes=1)
        self._api_calls[client_id] = self._clean_old_entries(
            self._api_calls[client_id], window
        )

        if len(self._api_calls[client_id]) >= self.max_api_calls:
            return False

        self._api_calls[client_id].append(datetime.utcnow())
        return True

    def get_retry_after(self, entries: list, window: timedelta) -> int:
        """Get seconds until the oldest entry expires."""
        if not entries:
            return 0
        oldest = min(entries)
        expires_at = oldest + window
        delta = (expires_at - datetime.utcnow()).total_seconds()
        return max(1, int(delta))


# Global rate limiter instance
rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware for API calls."""

    async def dispatch(self, request: Request, call_next):
        # Use client IP as identifier for general rate limiting
        client_id = request.client.host if request.client else "unknown"

        # Skip rate limiting for health checks and WebSocket
        if request.url.path in ("/api/health", "/", "/docs", "/openapi.json"):
            return await call_next(request)
        if request.url.path.startswith("/ws"):
            return await call_next(request)

        # Check API rate limit
        if not rate_limiter.check_api_rate(client_id):
            retry_after = rate_limiter.get_retry_after(
                rate_limiter._api_calls[client_id],
                timedelta(minutes=1),
            )
            logger.warning(f"[RateLimit] API rate limit exceeded for {client_id}")
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": "Too many API calls. Please slow down.",
                    "retry_after": retry_after,
                    "status": 429,
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
