from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Group

router = APIRouter(prefix="/groups", tags=["Groups"])

class GroupResponse(BaseModel):
    id: int
    name: str
    tenant_id: int

    class Config:
        from_attributes = True

@router.get("/", response_model=List[GroupResponse])
async def list_groups(db: AsyncSession = Depends(get_db)):
    """List all available groups."""
    stmt = select(Group).order_by(Group.name)
    result = await db.execute(stmt)
    return result.scalars().all()
