"""IP Validation Middleware for FastAPI"""
import logging
from typing import List, Optional, Callable
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.ip2location_client import IP2LocationClient

logger = logging.getLogger(__name__)

# Routes that bypass IP validation
EXCLUDED_ROUTES = [
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/favicon.ico",
]


class IPValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate source IP addresses against allowed countries.

    Extracts the client IP from headers (X-Forwarded-For, X-Real-IP) or
    direct connection, queries ip2location database for country, and
    blocks requests from non-allowed countries.
    """

    def __init__(
        self,
        app,
        ip2location_client: IP2LocationClient,
        allowed_countries: List[str],
        enabled: bool = True
    ):
        """
        Initialize IP validation middleware

        Args:
            app: FastAPI application
            ip2location_client: IP2Location client instance
            allowed_countries: List of allowed ISO country codes
            enabled: Whether validation is enabled
        """
        super().__init__(app)
        self.ip2location_client = ip2location_client
        self.allowed_countries = [c.upper() for c in allowed_countries]
        self.enabled = enabled

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request

        Checks headers in order:
        1. X-Forwarded-For (first IP in chain)
        2. X-Real-IP
        3. Direct client host

        Args:
            request: FastAPI request object

        Returns:
            Client IP address string
        """
        # Check X-Forwarded-For header (set by reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP in the chain (original client)
            ip = forwarded_for.split(",")[0].strip()
            logger.debug(f"Got IP from X-Forwarded-For: {ip}")
            return ip

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            logger.debug(f"Got IP from X-Real-IP: {real_ip}")
            return real_ip

        # Fall back to direct client host
        client_host = request.client.host if request.client else "unknown"
        logger.debug(f"Got IP from client.host: {client_host}")
        return client_host

    def _is_excluded_route(self, path: str) -> bool:
        """
        Check if route should bypass IP validation

        Args:
            path: Request path

        Returns:
            True if route should be excluded
        """
        # Exact match
        if path in EXCLUDED_ROUTES:
            return True

        # Prefix match for API docs
        if path.startswith("/docs") or path.startswith("/redoc"):
            return True

        return False

    async def dispatch(
        self,
        request: Request,
        call_next: Callable
    ) -> Response:
        """
        Process request through IP validation

        Args:
            request: FastAPI request
            call_next: Next middleware/handler

        Returns:
            Response object
        """
        # Skip if validation disabled
        if not self.enabled:
            return await call_next(request)

        # Skip excluded routes
        if self._is_excluded_route(request.url.path):
            return await call_next(request)

        # Extract client IP
        client_ip = self._get_client_ip(request)

        # Store IP in request state for downstream use
        request.state.source_ip = client_ip

        # Check if private IP (always allowed)
        if self.ip2location_client.is_private_ip(client_ip):
            request.state.source_country = "PRIVATE"
            logger.debug(f"Private IP {client_ip} - allowed")
            return await call_next(request)

        # Lookup country
        country_code = await self.ip2location_client.get_country_by_ip(client_ip)

        # Store country in request state
        request.state.source_country = country_code

        # If country lookup failed, log but allow (fail-open for availability)
        if country_code is None:
            logger.warning(
                f"Could not determine country for IP {client_ip} - allowing request"
            )
            return await call_next(request)

        # Check if country is allowed
        if country_code not in self.allowed_countries:
            logger.warning(
                f"Blocked request from IP {client_ip} (country: {country_code}). "
                f"Allowed countries: {self.allowed_countries}"
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": "Access denied",
                    "detail": f"Requests from {country_code} are not allowed",
                    "source_ip": client_ip,
                    "country_code": country_code
                }
            )

        logger.debug(
            f"Allowed request from IP {client_ip} (country: {country_code})"
        )

        return await call_next(request)


def get_request_ip_info(request: Request) -> dict:
    """
    Helper function to get IP info from request state

    Args:
        request: FastAPI request object

    Returns:
        Dictionary with source_ip and source_country
    """
    return {
        "source_ip": getattr(request.state, "source_ip", None),
        "source_country": getattr(request.state, "source_country", None)
    }
