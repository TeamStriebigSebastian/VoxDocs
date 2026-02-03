"""
Authentication API endpoints.
Implements login, refresh, logout per V1 requirements §4.1.
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from loguru import logger

from app.core.database import get_db
from app.core.auth import (
    verify_password,
    create_token_pair,
    decode_token,
    create_access_token,
    TokenPair
)
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.models.user_role import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])


# --- Request/Response Models ---

class LoginRequest(BaseModel):
    """Login credentials."""
    username: str
    password: str


class RefreshRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserResponse(BaseModel):
    """Current user info response."""
    id: int
    uuid: str
    username: str
    email: str
    tenant_id: int
    active: bool
    roles: list[dict]

    class Config:
        from_attributes = True


# --- Endpoints ---

@router.post("/login", response_model=TokenPair)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return access + refresh tokens.
    
    - Access token: 15 minutes
    - Refresh token: 14 days
    """
    # Find user by username
    user = await db.scalar(
        select(User)
        .options(selectinload(User.group_roles))
        .where(User.username == credentials.username)
    )
    
    if not user:
        logger.warning(f"Login failed: user '{credentials.username}' not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Verify password
    if not verify_password(credentials.password, user.password_hash):
        logger.warning(f"Login failed: invalid password for '{credentials.username}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Check if user is active
    if not user.active:
        logger.warning(f"Login failed: user '{credentials.username}' is inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Update last login
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Create tokens
    tokens = create_token_pair(user.id, user.tenant_id)
    
    logger.info(f"User '{credentials.username}' logged in successfully")
    return tokens


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Get a new access token using a refresh token.
    Also issues a new refresh token (token rotation).
    """
    token_data = decode_token(request.refresh_token)
    
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    if token_data.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type"
        )
    
    # Verify user still exists and is active
    user = await db.scalar(select(User).where(User.id == int(token_data.sub)))
    
    if not user or not user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Issue new token pair (token rotation for security)
    tokens = create_token_pair(user.id, user.tenant_id)
    
    logger.info(f"Token refreshed for user ID {user.id}")
    return tokens


@router.post("/logout")
async def logout():
    """
    Logout endpoint. 
    
    Note: With stateless JWTs, actual invalidation requires client-side
    token deletion. This endpoint is provided for API completeness.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get information about the currently authenticated user."""
    roles = [
        {
            "group_id": gr.group_id,
            "role": gr.role.value,
            "can_manage_users": gr.can_manage_users
        }
        for gr in current_user.group_roles
    ]
    
    return UserResponse(
        id=current_user.id,
        uuid=current_user.uuid,
        username=current_user.username,
        email=current_user.email,
        tenant_id=current_user.tenant_id,
        active=current_user.active,
        roles=roles
    )
