from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.dependencies import get_current_active_user, require_role
from app.models import User, UserRole, Tenant

router = APIRouter(prefix="/settings", tags=["Settings"])

class SettingsUpdate(BaseModel):
    default_language: str

class SettingsResponse(BaseModel):
    default_language: str
    tenant_name: str

@router.get("/", response_model=SettingsResponse)
async def read_settings(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # Determine which tenant/practice the user belongs to.
    # For V1, we assume single tenant or user.tenant_id
    stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    tenant = await db.scalar(stmt)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant settings not found")
    
    return SettingsResponse(
        default_language=tenant.default_language,
        tenant_name=tenant.name
    )

@router.put("/", response_model=SettingsResponse, dependencies=[Depends(require_role(UserRole.ADMIN))])
async def update_settings(
    settings_in: SettingsUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Tenant).where(Tenant.id == current_user.tenant_id)
    tenant = await db.scalar(stmt)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant settings not found")
    
    tenant.default_language = settings_in.default_language
    await db.commit()
    await db.refresh(tenant)
    
    return SettingsResponse(
        default_language=tenant.default_language,
        tenant_name=tenant.name
    )
