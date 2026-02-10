"""
Voice Assistant API — receives audio commands from the Android VoxDocs Voice Agent.

POST /api/voice/intake  —  upload audio + metadata for transcription & task creation
GET  /api/voice/cases    —  lightweight case list for the Android local cache
"""

import uuid
import shutil
import os
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from loguru import logger
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.config import settings
from app.models import Entry, CaseFile, User, AudioStatus, Task, TaskStatus, TaskType, UserRole

router = APIRouter(prefix="/voice", tags=["Voice Assistant"])


# ── Response models ──────────────────────────────────────────────────

class VoiceCaseItem(BaseModel):
    id: str         # uuid
    name: str       # title

class TaskItem(BaseModel):
    id: str
    title: str
    status: str

class IntakeResponse(BaseModel):
    caseId: str
    noteId: Optional[str] = None
    createdTasks: list = []
    message: str = "ok"


# ── POST /intake — audio command upload ──────────────────────────────

@router.post("/intake", response_model=IntakeResponse)
async def voice_intake(
    audio: UploadFile = File(...),
    meta: str = Form(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Receive a voice command recording from the Android agent.

    The audio is saved and queued for Whisper transcription (same pipeline
    as regular entries).  The `meta` JSON must include at least:
      - caseName  (string)
      - intent    ("CREATE" | "READ_TASKS")
    """
    try:
        metadata = json.loads(meta)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid meta JSON")

    case_name = metadata.get("caseName", "")
    case_id_hint = metadata.get("caseId", None)
    intent = metadata.get("intent", "CREATE")
    source = metadata.get("source", "phone")
    device_id = metadata.get("deviceId", "unknown")

    # ── Resolve case ─────────────────────────────────────────────

    case: Optional[CaseFile] = None

    # Prefer caseId if provided (already resolved on client)
    if case_id_hint:
        case = await db.scalar(
            select(CaseFile).where(CaseFile.uuid == case_id_hint)
        )

    # Fallback: fuzzy name match
    if not case and case_name:
        # Exact match first
        case = await db.scalar(
            select(CaseFile).where(
                func.lower(CaseFile.title) == case_name.lower()
            )
        )
        # Contains match
        if not case:
            case = await db.scalar(
                select(CaseFile).where(
                    func.lower(CaseFile.title).contains(case_name.lower())
                )
            )

    if not case:
        raise HTTPException(404, f"Case not found: '{case_name}'")

    # Verify user has access to this case's group
    user_group_ids = [gr.group_id for gr in current_user.group_roles]
    if case.group_id not in user_group_ids:
        raise HTTPException(403, "No access to this case")

    # ── READ_TASKS intent ────────────────────────────────────────

    if intent == "READ_TASKS":
        query = (
            select(Task)
            .where(Task.case_id == case.id, Task.status == TaskStatus.ACTIVE)
            .order_by(Task.created_at.desc())
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        return IntakeResponse(
            caseId=case.uuid,
            createdTasks=[
                {"id": t.uuid, "title": t.title, "status": t.status.value}
                for t in tasks
            ],
            message=f"{len(tasks)} open tasks for {case.title}",
        )

    # ── CREATE intent — save audio + create entry ────────────────

    entry_uuid = str(uuid.uuid4())

    # Save audio file
    audio_dir = os.path.join(settings.UPLOAD_DIR, "audio")
    os.makedirs(audio_dir, exist_ok=True)
    audio_ext = os.path.splitext(audio.filename or "recording.wav")[1] or ".wav"
    audio_key = f"{entry_uuid}{audio_ext}"
    audio_path = os.path.join(audio_dir, audio_key)

    with open(audio_path, "wb") as f:
        shutil.copyfileobj(audio.file, f)

    logger.info(f"Voice intake: saved audio {audio_key} ({os.path.getsize(audio_path)} bytes)")

    # Create entry with PENDING audio status (triggers Whisper worker)
    new_entry = Entry(
        uuid=entry_uuid,
        case_id=case.id,
        author_id=current_user.id,
        text=f"[Voice command from {source} / {device_id}]",
        audio_key=audio_key,
        audio_status=AudioStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(new_entry)
    await db.commit()
    await db.refresh(new_entry)

    logger.info(f"Voice intake: created entry {entry_uuid} for case {case.title}")

    return IntakeResponse(
        caseId=case.uuid,
        noteId=new_entry.uuid,
        message=f"Audio saved for {case.title}, transcription queued",
    )


# ── GET /cases — lightweight case list for Android cache ─────────

@router.get("/cases", response_model=List[VoiceCaseItem])
async def voice_cases(
    group_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return a flat list of cases (id + name) for the Android case cache.
    If group_id is specified, filter by group; otherwise return all accessible.
    """
    user_group_ids = [gr.group_id for gr in current_user.group_roles]

    query = select(CaseFile).where(CaseFile.group_id.in_(user_group_ids))
    if group_id and group_id in user_group_ids:
        query = select(CaseFile).where(CaseFile.group_id == group_id)

    result = await db.execute(query.order_by(CaseFile.title))
    cases = result.scalars().all()

    return [VoiceCaseItem(id=c.uuid, name=c.title) for c in cases]
