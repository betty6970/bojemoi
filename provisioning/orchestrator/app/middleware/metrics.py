"""Prometheus metrics middleware for FastAPI.

This middleware automatically tracks:
- Request count by method, endpoint, and status code
- Request duration
- Requests in progress
"""
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.metrics import (
    api_requests_total,
    api_request_duration,
    api_requests_in_progress,
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics for all HTTP requests."""

    # Endpoints to exclude from metrics (to avoid noise)
    EXCLUDED_PATHS = {
        "/metrics",
        "/health",
        "/favicon.ico",
    }

    def __init__(self, app, exclude_paths: set = None):
        """Initialize metrics middleware.

        Args:
            app: ASGI application
            exclude_paths: Additional paths to exclude from metrics
        """
        super().__init__(app)
        self.exclude_paths = self.EXCLUDED_PATHS.copy()
        if exclude_paths:
            self.exclude_paths.update(exclude_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        path = request.url.path
        method = request.method

        # Skip excluded paths
        if path in self.exclude_paths:
            return await call_next(request)

        # Normalize path for metrics (replace IDs with placeholders)
        endpoint = self._normalize_path(path)

        # Track in-progress requests
        api_requests_in_progress.labels(
            method=method,
            endpoint=endpoint
        ).inc()

        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            status_code = 500
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            api_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status_code=str(status_code)
            ).inc()

            api_request_duration.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Decrement in-progress counter
            api_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()

        return response

    def _normalize_path(self, path: str) -> str:
        """Normalize path by replacing dynamic segments with placeholders.

        This prevents high cardinality in metrics labels.

        Examples:
            /api/v1/deployments/123 -> /api/v1/deployments/{id}
            /api/v1/blockchain/blocks/456 -> /api/v1/blockchain/blocks/{id}
        """
        parts = path.split("/")
        normalized = []

        for i, part in enumerate(parts):
            if not part:
                normalized.append(part)
                continue

            # Check if this looks like an ID (numeric or UUID-like)
            if part.isdigit():
                normalized.append("{id}")
            elif self._looks_like_uuid(part):
                normalized.append("{uuid}")
            elif self._looks_like_hash(part):
                normalized.append("{hash}")
            else:
                normalized.append(part)

        return "/".join(normalized)

    def _looks_like_uuid(self, s: str) -> bool:
        """Check if string looks like a UUID."""
        if len(s) == 36 and s.count("-") == 4:
            return all(c in "0123456789abcdef-" for c in s.lower())
        return False

    def _looks_like_hash(self, s: str) -> bool:
        """Check if string looks like a hash (64 chars hex)."""
        if len(s) == 64:
            return all(c in "0123456789abcdef" for c in s.lower())
        return False
