"""Authentication API routes.

This module provides endpoints for:
- User login (JWT token generation)
- Token refresh
- User management (admin only)
- Password change
"""
from datetime import datetime, timezone
from typing import List
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.auth.models import (
    Token,
    UserCreate,
    UserUpdate,
    UserResponse,
    UserRole,
    RefreshRequest,
    PasswordChangeRequest,
    TokenData,
)
from app.auth.dependencies import (
    get_current_active_user,
    require_admin,
)
from app.config import settings


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


# In-memory user store for simplicity
# In production, this should be stored in the database
_users_db = {}


def _init_default_admin():
    """Initialize default admin user from environment."""
    if settings.AUTH_DEFAULT_ADMIN_USERNAME and settings.AUTH_DEFAULT_ADMIN_PASSWORD:
        _users_db[settings.AUTH_DEFAULT_ADMIN_USERNAME] = {
            "id": 1,
            "username": settings.AUTH_DEFAULT_ADMIN_USERNAME,
            "hashed_password": get_password_hash(settings.AUTH_DEFAULT_ADMIN_PASSWORD),
            "email": None,
            "full_name": "Default Admin",
            "role": UserRole.ADMIN,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": None,
            "last_login": None,
        }
        logger.info(f"Default admin user initialized: {settings.AUTH_DEFAULT_ADMIN_USERNAME}")


# Initialize default admin on module load
_init_default_admin()


def get_user(username: str) -> dict | None:
    """Get user by username from store."""
    return _users_db.get(username)


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate user with username and password.

    Args:
        username: User's username
        password: User's password

    Returns:
        User dict if authenticated, None otherwise
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate user and return JWT tokens.

    Uses OAuth2 password flow for compatibility with OpenAPI/Swagger UI.
    """
    user = authenticate_user(form_data.username, form_data.password)

    if not user:
        logger.warning(f"Failed login attempt for user: {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
        )

    # Update last login
    user["last_login"] = datetime.now(timezone.utc)

    # Create tokens
    token_data = {
        "sub": user["username"],
        "role": user["role"].value if isinstance(user["role"], UserRole) else user["role"],
        "scopes": [],
    }

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    logger.info(f"User logged in: {user['username']}")

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshRequest):
    """Refresh access token using refresh token."""
    payload = verify_token(request.refresh_token, token_type="refresh")

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    username = payload.get("sub")
    user = get_user(username)

    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    # Create new tokens
    token_data = {
        "sub": user["username"],
        "role": user["role"].value if isinstance(user["role"], UserRole) else user["role"],
        "scopes": [],
    }

    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    return Token(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_active_user)
):
    """Get current user information."""
    user = get_user(current_user.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user.get("email"),
        full_name=user.get("full_name"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user.get("last_login"),
    )


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: TokenData = Depends(get_current_active_user)
):
    """Change current user's password."""
    user = get_user(current_user.username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not verify_password(request.current_password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Update password
    user["hashed_password"] = get_password_hash(request.new_password)
    user["updated_at"] = datetime.now(timezone.utc)

    logger.info(f"Password changed for user: {user['username']}")

    return {"message": "Password changed successfully"}


# Admin-only endpoints

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: TokenData = Depends(require_admin)
):
    """List all users (admin only)."""
    return [
        UserResponse(
            id=user["id"],
            username=user["username"],
            email=user.get("email"),
            full_name=user.get("full_name"),
            role=user["role"],
            is_active=user["is_active"],
            created_at=user["created_at"],
            last_login=user.get("last_login"),
        )
        for user in _users_db.values()
    ]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: TokenData = Depends(require_admin)
):
    """Create a new user (admin only)."""
    if user_data.username in _users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    new_id = max((u["id"] for u in _users_db.values()), default=0) + 1

    user = {
        "id": new_id,
        "username": user_data.username,
        "hashed_password": get_password_hash(user_data.password),
        "email": user_data.email,
        "full_name": user_data.full_name,
        "role": user_data.role,
        "is_active": user_data.is_active,
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
        "last_login": None,
    }

    _users_db[user_data.username] = user
    logger.info(f"User created: {user_data.username} by {current_user.username}")

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user.get("email"),
        full_name=user.get("full_name"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user.get("last_login"),
    )


@router.put("/users/{username}", response_model=UserResponse)
async def update_user(
    username: str,
    user_data: UserUpdate,
    current_user: TokenData = Depends(require_admin)
):
    """Update a user (admin only)."""
    user = get_user(username)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user_data.email is not None:
        user["email"] = user_data.email
    if user_data.full_name is not None:
        user["full_name"] = user_data.full_name
    if user_data.password is not None:
        user["hashed_password"] = get_password_hash(user_data.password)
    if user_data.role is not None:
        user["role"] = user_data.role
    if user_data.is_active is not None:
        user["is_active"] = user_data.is_active

    user["updated_at"] = datetime.now(timezone.utc)

    logger.info(f"User updated: {username} by {current_user.username}")

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user.get("email"),
        full_name=user.get("full_name"),
        role=user["role"],
        is_active=user["is_active"],
        created_at=user["created_at"],
        last_login=user.get("last_login"),
    )


@router.delete("/users/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    username: str,
    current_user: TokenData = Depends(require_admin)
):
    """Delete a user (admin only)."""
    if username not in _users_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    del _users_db[username]
    logger.info(f"User deleted: {username} by {current_user.username}")
