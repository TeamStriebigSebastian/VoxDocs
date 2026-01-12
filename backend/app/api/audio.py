"""
Audio recording API endpoints.
"""

import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger
import aiofiles

from app.core.config import settings
from app.core.database import get_db
from app.models.audio import AudioRecording, ProcessingStatus
from app.services.encryption_service import encryption_service
from app.services.queue_service import queue_service

router = APIRouter()


class AudioUploadResponse(BaseModel):
    """Response model for audio upload."""
    id: int
    uuid: str
    status: str
    message: str
    queue_job_id: Optional[str] = None


class AudioRecordingResponse(BaseModel):
    """Response model for audio recording details."""
    id: int
    uuid: str
    status: str
    duration_seconds: Optional[float]
    recorded_at: datetime
    processing_started_at: Optional[datetime]
    processing_completed_at: Optional[datetime]
    has_transcription: bool


class AudioListResponse(BaseModel):
    """Response model for listing audio recordings."""
    recordings: List[AudioRecordingResponse]
    total: int
    page: int
    page_size: int


@router.post("/upload", response_model=AudioUploadResponse)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    practice_id: int = Form(...),
    room_id: Optional[int] = Form(None),
    user_id: Optional[int] = Form(None),
    process_immediately: bool = Form(False),
    recorded_at: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an audio recording for processing.

    Args:
        file: Audio file (WAV format recommended)
        practice_id: ID of the dental practice
        room_id: Optional treatment room ID
        user_id: Optional user ID who recorded
        process_immediately: If True, process immediately instead of queuing
        recorded_at: ISO timestamp of when recording was made (not upload time)
    """
    # Validate file type
    if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.ogg', '.webm')):
        raise HTTPException(
            status_code=400,
            detail="Unsupported audio format. Supported: WAV, MP3, M4A, OGG, WebM"
        )

    # Generate UUID for the recording
    recording_uuid = str(uuid.uuid4())
    logger.info(f"Processing upload: {recording_uuid}")

    # Save temporary file
    temp_path = settings.AUDIO_DIR / f"temp_{recording_uuid}{Path(file.filename).suffix}"
    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
            file_size = len(content)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save audio file")

    # Encrypt the file
    try:
        encrypted_filename = f"{recording_uuid}.enc"
        encrypted_path = settings.ENCRYPTED_DIR / encrypted_filename
        encryption_service.encrypt_file(temp_path, encrypted_path)

        # Remove temporary file
        temp_path.unlink()
    except Exception as e:
        logger.error(f"Failed to encrypt file: {e}")
        temp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Failed to encrypt audio file")

    # Get audio duration (simplified - would need actual audio processing)
    duration_seconds = None  # Will be set during processing

    # Parse recorded_at timestamp (when recording was made, not upload time)
    if recorded_at:
        try:
            # Handle ISO format with Z suffix or timezone offset
            actual_recorded_at = datetime.fromisoformat(recorded_at.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid recorded_at format: {recorded_at}, using current time")
            actual_recorded_at = datetime.utcnow()
    else:
        actual_recorded_at = datetime.utcnow()

    # Calculate expiration date
    expires_at = datetime.utcnow() + timedelta(days=settings.RETENTION_DAYS)

    # Create database record
    recording = AudioRecording(
        uuid=recording_uuid,
        original_filename=file.filename,
        encrypted_filename=encrypted_filename,
        file_size_bytes=file_size,
        duration_seconds=duration_seconds,
        practice_id=practice_id,
        room_id=room_id,
        recorded_by_user_id=user_id,
        recorded_at=actual_recorded_at,
        status=ProcessingStatus.PENDING,
        expires_at=expires_at
    )

    db.add(recording)
    await db.commit()
    await db.refresh(recording)

    # Add to processing queue
    queue_job = await queue_service.add_job(
        recording_id=recording.id,
        audio_path=str(encrypted_path),
        practice_id=practice_id,
        priority=10 if process_immediately else 0
    )

    # Update status to queued
    recording.status = ProcessingStatus.QUEUED
    await db.commit()

    # Process immediately if requested
    if process_immediately:
        background_tasks.add_task(queue_service.process_immediate, queue_job.id)

    logger.info(f"Audio uploaded and queued: {recording_uuid}")

    return AudioUploadResponse(
        id=recording.id,
        uuid=recording_uuid,
        status=recording.status.value,
        message="Audio uploaded and queued for processing",
        queue_job_id=queue_job.id
    )


@router.get("/{recording_uuid}", response_model=AudioRecordingResponse)
async def get_recording(
    recording_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Get details of an audio recording."""
    result = await db.execute(
        select(AudioRecording).where(AudioRecording.uuid == recording_uuid)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    return AudioRecordingResponse(
        id=recording.id,
        uuid=recording.uuid,
        status=recording.status.value,
        duration_seconds=recording.duration_seconds,
        recorded_at=recording.recorded_at,
        processing_started_at=recording.processing_started_at,
        processing_completed_at=recording.processing_completed_at,
        has_transcription=recording.transcription is not None
    )


@router.get("/", response_model=AudioListResponse)
async def list_recordings(
    practice_id: int,
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List audio recordings for a practice."""
    query = select(AudioRecording).where(
        AudioRecording.practice_id == practice_id,
        AudioRecording.is_deleted == False
    )

    if status:
        query = query.where(AudioRecording.status == ProcessingStatus(status))

    # Get total count
    count_result = await db.execute(
        select(AudioRecording.id).where(
            AudioRecording.practice_id == practice_id,
            AudioRecording.is_deleted == False
        )
    )
    total = len(count_result.all())

    # Apply pagination
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.order_by(AudioRecording.recorded_at.desc())

    result = await db.execute(query)
    recordings = result.scalars().all()

    return AudioListResponse(
        recordings=[
            AudioRecordingResponse(
                id=r.id,
                uuid=r.uuid,
                status=r.status.value,
                duration_seconds=r.duration_seconds,
                recorded_at=r.recorded_at,
                processing_started_at=r.processing_started_at,
                processing_completed_at=r.processing_completed_at,
                has_transcription=False  # Would need join to check
            )
            for r in recordings
        ],
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/{recording_uuid}")
async def delete_recording(
    recording_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Soft delete an audio recording."""
    result = await db.execute(
        select(AudioRecording).where(AudioRecording.uuid == recording_uuid)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Soft delete
    recording.is_deleted = True
    await db.commit()

    # Securely delete the encrypted file
    encrypted_path = settings.ENCRYPTED_DIR / recording.encrypted_filename
    if encrypted_path.exists():
        encryption_service.secure_delete(encrypted_path)

    logger.info(f"Recording deleted: {recording_uuid}")

    return {"status": "deleted", "uuid": recording_uuid}
