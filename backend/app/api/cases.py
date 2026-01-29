import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from loguru import logger
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models import CaseFile, CaseStatus, Group, User, UserRole

router = APIRouter(prefix="/cases", tags=["Cases"])

# --- Models ---

class CaseCreate(BaseModel):
    group_id: int
    title: str
    external_ref: Optional[str] = None

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    external_ref: Optional[str] = None
    status: Optional[str] = None # active, archived, locked

# --- Helper ---
def check_group_access(user: User, group_id: int) -> UserRole:
    """Return user's role in the group or raise 403."""
    # Check for Global Admin first (if applicable, though V1 uses explicit roles)
    for gr in user.group_roles:
        if gr.role == UserRole.ADMIN:
             return UserRole.ADMIN
        if gr.group_id == group_id:
            return gr.role
            
    raise HTTPException(status_code=403, detail="No access to this group")

# --- Endpoints ---

@router.get("/", response_model=List[dict])
async def list_cases(
    group_id: int = Query(..., description="Filter by Group ID (required in V1)"),
    status: Optional[str] = Query(None, description="Filter by status (active, archived, locked)"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List cases for a specific group.
    """
    try:
        # Verify group access
        check_group_access(current_user, group_id)

        query = select(CaseFile).where(CaseFile.group_id == group_id)
        
        if status:
            try:
                status_enum = CaseStatus(status)
                query = query.where(CaseFile.status == status_enum)
            except ValueError:
                pass 
                
        # Newer first
        query = query.order_by(desc(CaseFile.updated_at))
        
        result = await db.execute(query)
        cases = result.scalars().all()
        
        return [
            {
                "id": c.id,
                "uuid": c.uuid,
                "title": c.title,
                "external_ref": c.external_ref,
                "status": c.status.value,
                "updated_at": c.updated_at,
                "created_at": c.created_at
            }
            for c in cases
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing cases: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=dict)
async def create_case(
    case_in: CaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new case file."""
    try:
        role = check_group_access(current_user, case_in.group_id)
        
        # Viewers cannot create
        if role == UserRole.VIEWER:
             raise HTTPException(status_code=403, detail="Viewers cannot create cases")

        # Validate group exists
        group = await db.scalar(select(Group).where(Group.id == case_in.group_id))
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")

        new_case = CaseFile(
            uuid=str(uuid.uuid4()),
            group_id=case_in.group_id,
            title=case_in.title,
            external_ref=case_in.external_ref,
            status=CaseStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_case)
        await db.commit()
        await db.refresh(new_case)
        
        logger.info(f"Created case {new_case.uuid}")
        
        return {
            "id": new_case.id,
            "uuid": new_case.uuid,
            "title": new_case.title,
            "status": new_case.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating case: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{case_uuid}", response_model=dict)
async def get_case(
    case_uuid: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full case details."""
    try:
        query = select(CaseFile).where(CaseFile.uuid == case_uuid)
        result = await db.execute(query)
        case = result.scalar_one_or_none()
        
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        check_group_access(current_user, case.group_id)
            
        return {
            "id": case.id,
            "uuid": case.uuid,
            "group_id": case.group_id,
            "title": case.title,
            "external_ref": case.external_ref,
            "status": case.status.value,
            "created_at": case.created_at,
            "updated_at": case.updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting case: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{case_uuid}", response_model=dict)
async def update_case(
    case_uuid: str,
    case_in: CaseUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update case status or details (Superuser/Admin only for status)."""
    try:
        case = await db.scalar(select(CaseFile).where(CaseFile.uuid == case_uuid))
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        role = check_group_access(current_user, case.group_id)
        
        # Check permissions
        # Only Superuser/Admin can change status to Archived/Locked
        # User can rename? Let's restrict all updates to Superuser for V1 simplicity
        # except maybe Title?
        # Requirement: "Superuser... export, case file administration".
        
        role_hierarchy = {UserRole.ADMIN: 4, UserRole.SUPERUSER: 3, UserRole.USER: 2, UserRole.VIEWER: 1}
        user_level = role_hierarchy.get(role, 0)
        
        if user_level < 3: # Not Superuser
             raise HTTPException(status_code=403, detail="Requires Superuser privileges to modify case files")

        if case_in.title is not None:
            case.title = case_in.title
        if case_in.external_ref is not None:
            case.external_ref = case_in.external_ref
            
        if case_in.status is not None:
            try:
                new_status = CaseStatus(case_in.status)
                case.status = new_status
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid status")
                
        case.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(case)
        
        return {
            "id": case.id,
            "uuid": case.uuid,
            "title": case.title,
            "status": case.status.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating case: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
