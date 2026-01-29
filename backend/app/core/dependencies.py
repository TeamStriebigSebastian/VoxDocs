"""
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import decode_token
from app.models.user import User
from app.models.user_role import UserRole, UserGroupRole

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extract and validate the current user from JWT token.
    Raises 401 if token is invalid or missing.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token_data = decode_token(credentials.credentials)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if token_data.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user with group roles
    user = await db.scalar(
        select(User)
        .options(selectinload(User.group_roles))
        .where(User.id == int(token_data.sub))
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure the current user is active."""
    if not current_user.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Get current user if token provided, otherwise return None.
    Useful for endpoints that work both authenticated and anonymous.
    """
    if not credentials:
        return None
    
    token_data = decode_token(credentials.credentials)
    if not token_data or token_data.type != "access":
        return None
    
    user = await db.scalar(
        select(User)
        .options(selectinload(User.group_roles))
        .where(User.id == int(token_data.sub))
    )
    return user


def require_role(required_role: UserRole):
    """
    Dependency factory to require a minimum role level.
    Usage: Depends(require_role(UserRole.ADMIN))
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        # Check if user has the required role in any group
        user_roles = [gr.role for gr in current_user.group_roles]
        
        # Role hierarchy: ADMIN > SUPERUSER > USER > VIEWER
        role_hierarchy = {
            UserRole.ADMIN: 4,
            UserRole.SUPERUSER: 3,
            UserRole.USER: 2,
            UserRole.VIEWER: 1
        }
        
        required_level = role_hierarchy.get(required_role, 0)
        max_user_level = max(
            (role_hierarchy.get(r, 0) for r in user_roles),
            default=0
        )
        
        if max_user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role.value} role or higher"
            )
        
        return current_user
    
    return role_checker


def require_group_access(group_id: int):
    """
    Dependency factory to require access to a specific group.
    """
    async def group_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        user_group_ids = [gr.group_id for gr in current_user.group_roles]
        
        if group_id not in user_group_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this group"
            )
        
        return current_user
    
    return group_checker
