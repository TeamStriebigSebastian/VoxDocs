import uuid
import shutil
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from loguru import logger

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.models import Entry, CaseFile, User, AudioStatus, CategoryDefinition, UserRole

router = APIRouter(prefix="/entries", tags=["Entries"])

@router.get("/", response_model=List[dict])
async def list_entries(
    case_uuid: str = Query(..., description="Case UUID to fetch entries for"),
    skip: int = Query(0, description="Skip N entries"),
    limit: int = Query(20, description="Limit result size"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """List entries for a specific case file (Paginated, Newest first)."""
    try:
        # Resolve case UUID to ID
        case_result = await db.execute(select(CaseFile).where(CaseFile.uuid == case_uuid))
        case = case_result.scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        # Verify access to case's group
        user_group_ids = [gr.group_id for gr in current_user.group_roles]
        if case.group_id not in user_group_ids:
             raise HTTPException(status_code=403, detail="No access to this case")

        # Fetch entries
        # Order by created_at DESC (Newest first)
        query = select(Entry).options(selectinload(Entry.translations)).where(Entry.case_id == case.id).order_by(Entry.created_at.desc())
        
        # Apply pagination
        if limit is not None:
            query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        entries = result.scalars().all()
        
        return [
            {
                "id": e.id,
                "uuid": e.uuid,
                "text": e.text,
                "created_at": e.created_at,
                "author_id": e.author_id, # In real app resolve to name
                "has_audio": bool(e.audio_object_key),
                "audio_status": e.audio_status.value if e.audio_status else None,
                "has_image": bool(e.image_object_key),
                "structured_data": e.structured_data,
                "category_id": e.category_id,
                "version": e.version,
                "translations": [
                    {"language_code": t.language_code, "translated_text": t.translated_text}
                    for t in e.translations
                ]
            }
            for e in entries
        ]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing entries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=dict)
async def create_entry(
    case_uuid: str = Form(...),
    text: str = Form(""),
    category_id: Optional[int] = Form(None),
    structured_data: str = Form("{}"), # JSON string
    parent_entry_id: Optional[int] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new entry (Text + Optional Audio + Optional Category).
    Accepts multipart/form-data.
    """
    try:
        # Parse structured_data
        try:
            data_dict = json.loads(structured_data)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON in structured_data")

        # Resolve case
        case_result = await db.execute(select(CaseFile).where(CaseFile.uuid == case_uuid))
        case = case_result.scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
            
        # Verify access (Check Group Role)
        user_group_role = next((gr for gr in current_user.group_roles if gr.group_id == case.group_id), None)
        if not user_group_role:
             raise HTTPException(status_code=403, detail="No access to this case")
        
        # Verify write permission (Viewer cannot create entries)
        if user_group_role.role == UserRole.VIEWER:
            raise HTTPException(status_code=403, detail="Viewers cannot create entries")

        # Validate Category if provided
        if category_id:
            category = await db.get(CategoryDefinition, category_id)
            if not category:
                raise HTTPException(status_code=400, detail="Category not found")
            if category.group_id != case.group_id:
                 raise HTTPException(status_code=400, detail="Category belongs to a different group")

        # Handle Audio Upload
        audio_key = None
        audio_status = None
        
        if audio_file:
            # Generate safe filename
            file_ext = os.path.splitext(audio_file.filename)[1] or ".wav"
            filename = f"{uuid.uuid4()}{file_ext}"
            
            # Ensure storage dir exists (using settings or default)
            # Default to /app/storage/encrypted per requirements
            upload_dir = "/app/storage/encrypted"
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)
            
            audio_key = filename
            audio_status = AudioStatus.PENDING # Trigger for STT

        new_entry = Entry(
            uuid=str(uuid.uuid4()),
            case_id=case.id,
            category_id=category_id,
            author_id=current_user.id,
            text=text,
            structured_data=data_dict,
            audio_object_key=audio_key,
            audio_status=audio_status,
            version=1,
            parent_entry_id=parent_entry_id,
            created_at=datetime.utcnow()
        )
        
        db.add(new_entry)
        
        # Update case modified time
        case.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(new_entry)
        
        logger.info(f"Created entry {new_entry.uuid} for case {case.uuid} (Audio: {bool(audio_key)})")
        
        return {
            "uuid": new_entry.uuid,
            "created_at": new_entry.created_at,
            "status": "created",
            "has_audio": bool(audio_key)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating entry: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
