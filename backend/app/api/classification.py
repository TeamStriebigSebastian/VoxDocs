"""
Classification API endpoints.
Uses LLM-generated classifications stored during transcription processing.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
from datetime import datetime

from app.core.database import get_db
from app.models.audio import AudioRecording
from app.models.transcription import Transcription
from app.models.classification import Classification

router = APIRouter()


class ClassificationItemResponse(BaseModel):
    """Response model for a single classification."""
    id: int
    category: str
    text: str
    confidence: float
    is_verified: bool = False


class ClassificationResponse(BaseModel):
    """Response model for classifications."""
    recording_uuid: str
    total_entities: int
    classifications: List[ClassificationItemResponse]
    llm_processed: bool


@router.get("/{recording_uuid}", response_model=ClassificationResponse)
async def get_classifications(
    recording_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Get LLM-generated classifications for a recording's transcription."""
    result = await db.execute(
        select(AudioRecording)
        .options(
            selectinload(AudioRecording.transcription)
            .selectinload(Transcription.classifications)
        )
        .where(AudioRecording.uuid == recording_uuid)
    )
    recording = result.scalar_one_or_none()

    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    if not recording.transcription:
        raise HTTPException(status_code=404, detail="Transcription not available")

    transcription = recording.transcription

    return ClassificationResponse(
        recording_uuid=recording_uuid,
        total_entities=len(transcription.classifications),
        classifications=[
            ClassificationItemResponse(
                id=c.id,
                category=c.category,
                text=c.text,
                confidence=c.confidence,
                is_verified=c.is_verified
            )
            for c in transcription.classifications
        ],
        llm_processed=transcription.llm_processed is not None
    )


@router.post("/{recording_uuid}/{classification_id}/verify")
async def verify_classification(
    recording_uuid: str,
    classification_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Verify a classification as correct (for training feedback)."""
    result = await db.execute(
        select(Classification).where(Classification.id == classification_id)
    )
    classification = result.scalar_one_or_none()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    classification.is_verified = True
    classification.verified_at = datetime.utcnow()

    await db.commit()

    return {"status": "verified", "classification_id": classification_id}


@router.get("/categories")
async def get_categories():
    """Get all classification categories used by LLM."""
    return {
        "categories": [
            {"type": "befund", "name": "Befund", "description": "Klinische Befunde und Diagnosen"},
            {"type": "behandlung", "name": "Behandlung", "description": "Durchgeführte Behandlungsschritte"},
            {"type": "planung", "name": "Planung", "description": "Geplante Maßnahmen und Empfehlungen"},
            {"type": "anamnese", "name": "Anamnese", "description": "Patienteninformationen und Vorgeschichte"},
            {"type": "aufgabe", "name": "Aufgabe", "description": "Aufgaben für den nächsten Termin"},
        ]
    }
