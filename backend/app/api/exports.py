"""
Case Export API - Download case data as ZIP (CSV + Photos)
"""

import io
import csv
import zipfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.config import settings
from app.models import CaseFile, Entry, Task, User, CategoryDefinition

router = APIRouter(prefix="/exports", tags=["Exports"])


@router.get("/case/{case_uuid}")
async def export_case(
    case_uuid: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Export a case as a ZIP file containing:
    - data.csv: All tasks and entries
    - images/: All attached images
    """
    # 1. Fetch case and verify access
    case_result = await db.execute(
        select(CaseFile).where(CaseFile.uuid == case_uuid)
    )
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Verify user has access to this case's group
    user_group_ids = [gr.group_id for gr in current_user.group_roles]
    if case.group_id not in user_group_ids:
        raise HTTPException(status_code=403, detail="No access to this case")
    
    # 2. Fetch all tasks
    tasks_result = await db.execute(
        select(Task).where(Task.case_id == case.id).order_by(Task.created_at)
    )
    tasks = tasks_result.scalars().all()
    
    # 3. Fetch all entries with categories and translations
    entries_result = await db.execute(
        select(Entry)
        .options(
            selectinload(Entry.category_definition),
            selectinload(Entry.translations)
        )
        .where(Entry.case_id == case.id)
        .order_by(Entry.created_at)
    )
    entries = entries_result.scalars().all()
    
    # 4. Build CSV in memory
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    
    # Header
    writer.writerow([
        "type",
        "category_name",
        "creation_date",
        "finish_date",
        "content",
        "path_to_picture"
    ])
    
    # Track images to include
    images_to_include = []  # List of (filename, entry_uuid)
    
    # Write tasks
    for task in tasks:
        writer.writerow([
            "task",
            "",  # No category for tasks
            task.created_at.isoformat() if task.created_at else "",
            task.last_completed_at.isoformat() if task.last_completed_at else "",
            task.title,
            ""  # No image for tasks
        ])
    
    # Build parent-child mapping
    parent_entries = [e for e in entries if not e.parent_entry_id]
    child_entries_by_parent = {}
    for e in entries:
        if e.parent_entry_id:
            if e.parent_entry_id not in child_entries_by_parent:
                child_entries_by_parent[e.parent_entry_id] = []
            child_entries_by_parent[e.parent_entry_id].append(e)
    
    # Write entries (only root entries, with child images merged)
    for entry in parent_entries:
        category_name = entry.category_definition.name if entry.category_definition else ""
        
        # Collect all images: own image + child attachment images
        image_paths = []
        
        if entry.image_object_key:
            image_paths.append(f"images/{entry.image_object_key}")
            images_to_include.append((entry.image_object_key, entry.uuid))
        
        # Add child attachment images
        children = child_entries_by_parent.get(entry.id, [])
        for child in children:
            if child.image_object_key:
                image_paths.append(f"images/{child.image_object_key}")
                images_to_include.append((child.image_object_key, child.uuid))
        
        # Build content including translations
        content_text = entry.text or ""
        if entry.translations:
            # Sort by language for consistency
            sorted_translations = sorted(entry.translations, key=lambda t: t.language_code)
            for t in sorted_translations:
                content_text += f"\n\n[Translation ({t.language_code.upper()})]: {t.translated_text}"

        writer.writerow([
            "entry",
            category_name,
            entry.created_at.isoformat() if entry.created_at else "",
            "",  # No finish date for entries
            content_text,
            "; ".join(image_paths)  # Multiple images separated by semicolon
        ])
    
    csv_content = csv_buffer.getvalue()
    csv_buffer.close()
    
    # 5. Create ZIP in memory
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Add CSV
        zf.writestr("data.csv", csv_content)
        
        # Add images
        for filename, entry_uuid in images_to_include:
            image_path = settings.ENCRYPTED_DIR / filename
            if image_path.exists():
                zf.write(image_path, f"images/{filename}")
            else:
                logger.warning(f"Image not found during export: {image_path}")
    
    zip_buffer.seek(0)
    
    # 6. Generate filename
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in case.title)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_title}_{timestamp}.zip"
    
    logger.info(f"Exported case {case_uuid} ({len(tasks)} tasks, {len(entries)} entries, {len(images_to_include)} images)")
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
