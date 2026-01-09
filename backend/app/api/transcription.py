"""
Transcription API endpoints.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.core.database import get_db
from app.models.audio import AudioRecording
from app.models.transcription import Transcription, TranscriptionSegment
from app.services.encryption_service import encryption_service
from app.services.whisper_service import whisper_service
from app.services.classification_service import classifier
from app.core.config import settings

router = APIRouter()


class TranscriptionSegmentResponse(BaseModel):
    """Response model for transcription segment."""
    start: float
    end: float
    text: str
    confidence: Optional[float]


class TranscriptionResponse(BaseModel):
    """Response model for transcription."""
    id: int
    recording_uuid: str
    full_text: str
    language: str
    processing_time: Optional[float]
    confidence: Optional[float]
    segments: List[TranscriptionSegmentResponse]
    created_at: datetime
    correction_count: int


class TranscriptionCorrectionRequest(BaseModel):
    """Request model for correcting transcription."""
    corrected_text: str
    segment_id: Optional[int] = None


@router.get("/{recording_uuid}", response_model=TranscriptionResponse)
async def get_transcription(
    recording_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Get transcription for a recording."""
    result = await db.execute(
        select(AudioRecording)
        .options(selectinload(AudioRecording.transcription).selectinload(Transcription.segments))
        .where(AudioRecording.uuid == recording_uuid)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not recording.transcription:
        raise HTTPException(status_code=404, detail="Transcription not available yet")

    transcription = recording.transcription

    return TranscriptionResponse(
        id=transcription.id,
        recording_uuid=recording_uuid,
        full_text=transcription.full_text,
        language=transcription.language,
        processing_time=transcription.processing_time_seconds,
        confidence=transcription.confidence_score,
        segments=[
            TranscriptionSegmentResponse(
                start=seg.start_time,
                end=seg.end_time,
                text=seg.text,
                confidence=seg.confidence
            )
            for seg in transcription.segments
        ],
        created_at=transcription.created_at,
        correction_count=transcription.correction_count
    )


@router.post("/{recording_uuid}/process")
async def process_transcription(
    recording_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger transcription processing for a recording.
    Useful for testing or immediate processing needs.
    """
    result = await db.execute(
        select(AudioRecording).where(AudioRecording.uuid == recording_uuid)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if recording.transcription:
        raise HTTPException(status_code=400, detail="Transcription already exists")

    logger.info(f"Processing transcription for: {recording_uuid}")

    # Decrypt the audio file
    encrypted_path = settings.ENCRYPTED_DIR / recording.encrypted_filename
    if not encrypted_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    try:
        # Decrypt to temporary file
        decrypted_path = encryption_service.decrypt_file(encrypted_path)

        # Transcribe using Whisper with dental vocabulary boost
        transcription_result = whisper_service.transcribe_with_dental_boost(decrypted_path)

        # Clean up decrypted file
        decrypted_path.unlink()

        # Update recording duration
        recording.duration_seconds = transcription_result.segments[-1]["end"] if transcription_result.segments else None

        # Create transcription record
        transcription = Transcription(
            recording_id=recording.id,
            full_text=transcription_result.text,
            language=transcription_result.language,
            whisper_model=settings.WHISPER_MODEL,
            processing_time_seconds=transcription_result.processing_time,
            confidence_score=transcription_result.confidence
        )
        db.add(transcription)
        await db.flush()

        # Create segments
        for seg in transcription_result.segments:
            segment = TranscriptionSegment(
                transcription_id=transcription.id,
                text=seg["text"],
                start_time=seg["start"],
                end_time=seg["end"],
                confidence=seg["confidence"],
                word_timestamps=seg.get("words")
            )
            db.add(segment)

        # Update recording status
        recording.status = "completed"
        recording.processing_completed_at = datetime.utcnow()

        await db.commit()

        logger.info(f"Transcription completed for: {recording_uuid}")

        return {
            "status": "completed",
            "transcription_id": transcription.id,
            "text_preview": transcription_result.text[:200] + "..." if len(transcription_result.text) > 200 else transcription_result.text,
            "processing_time": transcription_result.processing_time
        }

    except Exception as e:
        logger.error(f"Transcription failed for {recording_uuid}: {e}")
        recording.status = "failed"
        recording.error_message = str(e)
        await db.commit()
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


@router.post("/{recording_uuid}/correct", response_model=TranscriptionResponse)
async def correct_transcription(
    recording_uuid: str,
    correction: TranscriptionCorrectionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a correction for a transcription.
    This is used for the feedback loop to improve the model.
    """
    result = await db.execute(
        select(AudioRecording)
        .options(selectinload(AudioRecording.transcription).selectinload(Transcription.segments))
        .where(AudioRecording.uuid == recording_uuid)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not recording.transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    transcription = recording.transcription

    # Log the correction for training
    logger.info(f"Correction submitted for {recording_uuid}")
    logger.debug(f"Original: {transcription.full_text[:100]}...")
    logger.debug(f"Corrected: {correction.corrected_text[:100]}...")

    # Update transcription
    if correction.segment_id:
        # Update specific segment
        for seg in transcription.segments:
            if seg.id == correction.segment_id:
                seg.text = correction.corrected_text
                break
        # Rebuild full text from segments
        transcription.full_text = " ".join(seg.text for seg in transcription.segments)
    else:
        # Update full text
        transcription.full_text = correction.corrected_text

    transcription.correction_count += 1
    transcription.last_corrected_at = datetime.utcnow()

    await db.commit()
    await db.refresh(transcription)

    return TranscriptionResponse(
        id=transcription.id,
        recording_uuid=recording_uuid,
        full_text=transcription.full_text,
        language=transcription.language,
        processing_time=transcription.processing_time_seconds,
        confidence=transcription.confidence_score,
        segments=[
            TranscriptionSegmentResponse(
                start=seg.start_time,
                end=seg.end_time,
                text=seg.text,
                confidence=seg.confidence
            )
            for seg in transcription.segments
        ],
        created_at=transcription.created_at,
        correction_count=transcription.correction_count
    )


@router.get("/{recording_uuid}/download")
async def download_transcription(
    recording_uuid: str,
    format: str = "txt",
    db: AsyncSession = Depends(get_db)
):
    """Download transcription as text or SRT file."""
    result = await db.execute(
        select(AudioRecording)
        .options(selectinload(AudioRecording.transcription).selectinload(Transcription.segments))
        .where(AudioRecording.uuid == recording_uuid)
    )
    recording = result.scalar_one_or_none()

    if not recording or not recording.transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")

    transcription = recording.transcription

    if format == "txt":
        return {
            "content": transcription.full_text,
            "filename": f"{recording_uuid}.txt"
        }
    elif format == "srt":
        # Generate SRT format
        srt_content = []
        for i, seg in enumerate(transcription.segments, 1):
            start = _format_srt_time(seg.start_time)
            end = _format_srt_time(seg.end_time)
            srt_content.append(f"{i}\n{start} --> {end}\n{seg.text}\n")
        return {
            "content": "\n".join(srt_content),
            "filename": f"{recording_uuid}.srt"
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'txt' or 'srt'")


def _format_srt_time(seconds: float) -> str:
    """Format seconds to SRT timestamp format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
