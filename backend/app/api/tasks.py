from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from loguru import logger
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models import Task, CaseFile, User, TaskType, TaskStatus, UserRole

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# --- Pydantic Models ---
class TaskCreate(BaseModel):
    case_uuid: str
    title: str
    task_type: TaskType
    repeat_interval_days: Optional[int] = None

class TaskUpdateStatus(BaseModel):
    status: TaskStatus

class TaskTranslationResponse(BaseModel):
    language_code: str
    title: str

    class Config:
        from_attributes = True

class TaskResponse(BaseModel):
    id: int
    uuid: str
    title: str
    task_type: TaskType
    status: TaskStatus
    repeat_interval_days: Optional[int]
    created_at: datetime
    next_due_at: Optional[datetime]
    translations: List[TaskTranslationResponse] = []

    class Config:
        from_attributes = True

# --- Endpoints ---

@router.post("/", response_model=TaskResponse)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new task for a case."""
    try:
        # Resolve case
        case = await db.scalar(select(CaseFile).where(CaseFile.uuid == task_in.case_uuid))
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Verify access
        user_group_role = next((gr for gr in current_user.group_roles if gr.group_id == case.group_id), None)
        if not user_group_role:
             raise HTTPException(status_code=403, detail="No access to this case")
        
        # Verify write permission
        if user_group_role.role == UserRole.VIEWER:
             raise HTTPException(status_code=403, detail="Viewers cannot create tasks")

        new_task = Task(
            case_id=case.id,
            title=task_in.title,
            task_type=task_in.task_type,
            status=TaskStatus.ACTIVE,
            repeat_interval_days=task_in.repeat_interval_days,
            created_by=current_user.id,
            created_at=datetime.utcnow()
        )
        
        db.add(new_task)
        await db.commit()
        await db.refresh(new_task)
        
        # Explicitly set empty translations to avoid MissingGreenlet on response serialization
        # or we could reload with selectinload, but that's an extra query for nothing.
        new_task.translations = []
        
        return new_task

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    case_uuid: str = Query(..., description="Filter by Case UUID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List tasks for a case."""
    try:
        case = await db.scalar(select(CaseFile).where(CaseFile.uuid == case_uuid))
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        # Verify access
        if case.group_id not in [gr.group_id for gr in current_user.group_roles]:
             raise HTTPException(status_code=403, detail="No access to this case")

        query = select(Task).options(selectinload(Task.translations)).where(Task.case_id == case.id).order_by(Task.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: int,
    status_in: TaskUpdateStatus,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update task status (e.g. complete)."""
    try:
        # Eager load translations to avoid MissingGreenlet
        query = select(Task).options(selectinload(Task.translations)).where(Task.id == task_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
            
        # Verify access via case -> group
        # Need to fetch case to check group
        case = await db.get(CaseFile, task.case_id)
        if not case:
             # Should not happen if foreign keys are correct
             raise HTTPException(status_code=404, detail="Case not found")

        user_group_role = next((gr for gr in current_user.group_roles if gr.group_id == case.group_id), None)
        if not user_group_role:
             raise HTTPException(status_code=403, detail="No access to this case")
             
        if user_group_role.role == UserRole.VIEWER:
             raise HTTPException(status_code=403, detail="Viewers cannot update tasks")

        task.status = status_in.status
        if status_in.status == TaskStatus.COMPLETED:
            task.last_completed_at = datetime.utcnow()
            
        await db.commit()
        await db.refresh(task)
        return task
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating task: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
