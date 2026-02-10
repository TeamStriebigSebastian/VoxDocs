import uuid
import shutil
import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Body, File, UploadFile, Form
from fastapi.responses import FileResponse
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
        query = select(Entry).options(
            selectinload(Entry.translations),
            selectinload(Entry.author),
            selectinload(Entry.parent)
        ).where(Entry.case_id == case.id).order_by(Entry.created_at.desc())
        
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
                "author_id": e.author_id,
                "author_name": e.author.username if e.author else f"User {e.author_id}",
                "has_audio": bool(e.audio_object_key),
                "audio_status": e.audio_status.value if e.audio_status else None,
                "has_image": bool(e.image_object_key),
                "structured_data": e.structured_data,
                "category_id": e.category_id,
                "version": e.version,
                "parent_entry_id": e.parent_entry_id,
                "parent_entry_uuid": e.parent.uuid if e.parent else None,
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
    parent_entry_uuid: Optional[str] = Form(None),  # UUID-based linking (preferred)
    entry_uuid: Optional[str] = Form(None), # Allow client to specify UUID (for offline sync)
    audio_file: Optional[UploadFile] = File(None),
    image_file: Optional[UploadFile] = File(None),
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

        # Resolve parent_entry_uuid to parent_entry_id if provided
        resolved_parent_id = parent_entry_id
        if parent_entry_uuid:
            parent_result = await db.execute(
                select(Entry).where(Entry.uuid == parent_entry_uuid)
            )
            parent_entry = parent_result.scalar_one_or_none()
            if parent_entry:
                resolved_parent_id = parent_entry.id
            else:
                logger.warning(f"Parent entry UUID not found: {parent_entry_uuid}")

        # Handle Audio Upload
        audio_key = None
        audio_status = None
        
        if audio_file:
            # Generate safe filename
            file_ext = os.path.splitext(audio_file.filename)[1] or ".wav"
            filename = f"{uuid.uuid4()}{file_ext}"
            
            # Ensure storage dir exists (using settings)
            upload_dir = settings.ENCRYPTED_DIR
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(audio_file.file, buffer)
            
            audio_key = filename
            audio_status = AudioStatus.PENDING # Trigger for STT

        # Handle Image Upload
        image_key = None
        if image_file:
            file_ext = os.path.splitext(image_file.filename)[1] or ".jpg"
            filename = f"{uuid.uuid4()}{file_ext}"
            
            upload_dir = settings.ENCRYPTED_DIR
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(image_file.file, buffer)
            
            image_key = filename

        new_entry = Entry(
            uuid=entry_uuid or str(uuid.uuid4()),
            case_id=case.id,
            category_id=category_id,
            author_id=current_user.id,
            text=text,
            structured_data=data_dict,
            audio_object_key=audio_key,
            audio_status=audio_status,
            image_object_key=image_key,
            version=1,
            parent_entry_id=resolved_parent_id,
            created_at=datetime.utcnow()
        )
        
        db.add(new_entry)
        
        # Update case modified time
        case.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(new_entry)
        
        logger.info(f"Created entry {new_entry.uuid} for case {case.uuid} (Audio: {bool(audio_key)})")

        # RAG Ingestion (Text only, audio handles its own ingestion)
        # Only ingest if there is text and it's NOT a pending audio (which starts empty/minimal)
        # If user posts text+audio, we might overlap. 
        # But usually CreateEntry with audio has empty text or description. 
        # Let's ingest if text is substantial? Or just if no audio_file.
        if text and not audio_file:
            try:
                from mcp_server.tools.ingest import execute_ingest
                
                cat_names = []
                if category_id and 'category' in locals() and category:
                    cat_names = [category.name]
                
                await execute_ingest(
                    case_id=case.uuid,
                    text=text,
                    group_id=str(case.group_id),
                    author=current_user.username,
                    source_type="note",
                    source_ref=new_entry.uuid,
                    categories=cat_names
                )
                logger.info(f"Ingested text entry {new_entry.uuid} into RAG")
            except Exception as ingest_err:
                logger.error(f"RAG Ingestion for text entry failed: {ingest_err}")
        
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

@router.get("/{entry_uuid}/image")
async def get_entry_image(
    entry_uuid: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Serve the image file for an entry."""
    entry = await get_entry_and_verify_access(entry_uuid, current_user, db)
    
    if not entry.image_object_key:
        raise HTTPException(status_code=404, detail="No image attached to this entry")
        
    file_path = settings.ENCRYPTED_DIR / entry.image_object_key
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found on server")
        
    return FileResponse(file_path, media_type="image/jpeg")

@router.get("/{entry_uuid}/audio")
async def get_entry_audio(
    entry_uuid: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Serve the audio file for an entry."""
    entry = await get_entry_and_verify_access(entry_uuid, current_user, db)
    
    if not entry.audio_object_key:
        raise HTTPException(status_code=404, detail="No audio attached to this entry")
        
    file_path = settings.ENCRYPTED_DIR / entry.audio_object_key
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on server")
        
    return FileResponse(file_path, media_type="audio/wav")

async def get_entry_and_verify_access(entry_uuid: str, current_user: User, db: AsyncSession) -> Entry:
    """Helper to fetch entry and verify user access."""
    # Fetch entry with case loaded
    result = await db.execute(
        select(Entry).options(selectinload(Entry.case_file)).where(Entry.uuid == entry_uuid)
    )
    entry = result.scalar_one_or_none()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
        
    # Verify Access
    # Check if user has role in case.group_id
    user_group_ids = [gr.group_id for gr in current_user.group_roles]
    if entry.case_file.group_id not in user_group_ids:
        raise HTTPException(status_code=403, detail="No access to this case")
        
    return entry
