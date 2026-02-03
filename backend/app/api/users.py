from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.auth import get_password_hash
from app.core.dependencies import get_current_active_user, require_role
from app.models import User, UserGroupRole, UserRole

router = APIRouter(prefix="/users", tags=["Users"])

# --- Pydantic Models ---

class UserBase(BaseModel):
    username: str
    email: Optional[str] = None
    is_active: bool = True
    preferred_language: str = "de"

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.USER
    group_id: int = 1  # Default to generic group for V1

class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None
    group_id: Optional[int] = 1
    preferred_language: Optional[str] = None

class UserResponse(UserBase):
    id: int
    is_superuser: bool
    roles: List[str] = []

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Re-fetch with roles to be sure
    user = await db.scalar(
        select(User)
        .options(selectinload(User.group_roles))
        .where(User.id == current_user.id)
    )
    return _map_user_response(user)


@router.get("/", response_model=List[UserResponse], dependencies=[Depends(require_role(UserRole.ADMIN))])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).options(selectinload(User.group_roles)).offset(skip).limit(limit)
    users = await db.scalars(stmt)
    return [_map_user_response(u) for u in users]


@router.post("/", response_model=UserResponse, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if username exists
    existing = await db.scalar(select(User).where(User.username == user_in.username))
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    # Create User
    hashed_password = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_password,
        active=user_in.is_active,
        preferred_language=user_in.preferred_language,
        tenant_id=current_user.tenant_id
        # is_superuser computed from roles
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Assign Role in Default Group
    user_role = UserGroupRole(
        user_id=user.id,
        group_id=user_in.group_id,
        role=user_in.role
    )
    db.add(user_role)
    await db.commit()
    
    # Reload with roles
    await db.refresh(user, attribute_names=["group_roles"])
    return _map_user_response(user)


@router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def update_user(
    user_id: int,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db)
):
    user = await db.scalar(select(User).options(selectinload(User.group_roles)).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.is_active is not None:
        user.active = user_in.is_active
    
    if user_in.password:
        user.password_hash = get_password_hash(user_in.password)
        
    if user_in.preferred_language:
        user.preferred_language = user_in.preferred_language

    if user_in.role and user_in.group_id:
        # Update or Create Role for this group
        # simple V1 logic: clear existing roles for group and add new one
        # Ideally we find the specific role entry
        stmt = select(UserGroupRole).where(
            UserGroupRole.user_id == user_id, 
            UserGroupRole.group_id == user_in.group_id
        )
        existing_role = await db.scalar(stmt)
        if existing_role:
            existing_role.role = user_in.role
        else:
            new_role = UserGroupRole(
                user_id=user.id,
                group_id=user_in.group_id,
                role=user_in.role
            )
            db.add(new_role)
            
    await db.commit()
    await db.refresh(user, attribute_names=["group_roles"])
    return _map_user_response(user)


def _map_user_response(user: User) -> UserResponse:
    # Flatten roles for simple UI response
    roles = [gr.role.value for gr in user.group_roles] if user.group_roles else []
    
    # Compute superuser status from roles
    is_superuser = any(r == UserRole.ADMIN for r in roles)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.active,
        preferred_language=user.preferred_language,
        is_superuser=is_superuser,
        roles=roles
    )
