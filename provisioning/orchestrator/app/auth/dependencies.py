"""FastAPI authentication dependencies.

This module provides:
- OAuth2 bearer token extraction
- Current user dependency
- Role-based access control
- API key authentication
"""
from typing import Optional, List
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, APIKeyHeader

from app.auth.security import verify_token
from app.auth.models import UserRole, TokenData
from app.config import settings


logger = logging.getLogger(__name__)

# OAuth2 scheme for bearer token authentication
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False  # Don't auto-raise, we'll handle it
)

# API key header scheme
api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False
)


async def get_token_data(
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[TokenData]:
    """Extract and validate token data from bearer token.

    Args:
        token: Bearer token from Authorization header

    Returns:
        TokenData if valid, None otherwise
    """
    if not token:
        return None

    payload = verify_token(token, token_type="access")
    if not payload:
        return None

    username = payload.get("sub")
    role = payload.get("role")
    scopes = payload.get("scopes", [])

    if not username:
        return None

    return TokenData(
        username=username,
        role=UserRole(role) if role else None,
        scopes=scopes
    )


async def get_current_user(
    token_data: Optional[TokenData] = Depends(get_token_data),
    api_key: Optional[str] = Depends(api_key_header)
) -> TokenData:
    """Get current authenticated user from token or API key.

    This is the main authentication dependency. Use it to protect
    endpoints that require authentication.

    Args:
        token_data: Extracted token data from bearer token
        api_key: API key from X-API-Key header

    Returns:
        TokenData for the authenticated user

    Raises:
        HTTPException: If not authenticated
    """
    # Try bearer token first
    if token_data:
        return token_data

    # Try API key authentication
    if api_key:
        # Check against configured API keys
        if api_key in settings.API_KEYS:
            key_config = settings.API_KEYS[api_key]
            return TokenData(
                username=f"apikey:{key_config.get('name', 'unknown')}",
                role=UserRole(key_config.get("role", "viewer")),
                scopes=key_config.get("scopes", [])
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_active_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """Get current active user.

    Additional check to ensure user is active (not disabled).
    For now, we assume all authenticated users are active.

    Args:
        current_user: Current authenticated user

    Returns:
        TokenData if user is active

    Raises:
        HTTPException: If user is inactive
    """
    # In a real implementation, you would check the database
    # to see if the user is still active
    return current_user


def require_role(allowed_roles: List[UserRole]):
    """Dependency factory for role-based access control.

    Usage:
        @app.get("/admin-only")
        async def admin_endpoint(
            user: TokenData = Depends(require_role([UserRole.ADMIN]))
        ):
            ...

    Args:
        allowed_roles: List of roles that can access the endpoint

    Returns:
        Dependency function that checks user role
    """
    async def role_checker(
        current_user: TokenData = Depends(get_current_active_user)
    ) -> TokenData:
        if current_user.role not in allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.username} "
                f"(role: {current_user.role}, required: {allowed_roles})"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return current_user

    return role_checker


# Pre-built role dependencies for convenience
require_admin = require_role([UserRole.ADMIN])
require_operator = require_role([UserRole.ADMIN, UserRole.OPERATOR])
require_viewer = require_role([UserRole.ADMIN, UserRole.OPERATOR, UserRole.VIEWER])


async def get_optional_user(
    token_data: Optional[TokenData] = Depends(get_token_data),
    api_key: Optional[str] = Depends(api_key_header)
) -> Optional[TokenData]:
    """Get current user if authenticated, None otherwise.

    Use this for endpoints that work differently for authenticated
    vs anonymous users.

    Args:
        token_data: Extracted token data
        api_key: API key from header

    Returns:
        TokenData if authenticated, None otherwise
    """
    if token_data:
        return token_data

    if api_key and api_key in settings.API_KEYS:
        key_config = settings.API_KEYS[api_key]
        return TokenData(
            username=f"apikey:{key_config.get('name', 'unknown')}",
            role=UserRole(key_config.get("role", "viewer")),
            scopes=key_config.get("scopes", [])
        )

    return None
