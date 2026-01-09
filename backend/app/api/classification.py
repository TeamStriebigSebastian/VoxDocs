"""
Classification API endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger

from app.core.database import get_db
from app.models.audio import AudioRecording
from app.models.transcription import Transcription
from app.models.classification import Classification, ClassificationCategory, CategoryType
from app.services.classification_service import classifier, ClassificationResult

router = APIRouter()


class ClassificationItemResponse(BaseModel):
    """Response model for a single classification."""
    id: Optional[int]
    category: str
    extracted_text: str
    normalized_value: Optional[str]
    confidence: float
    tooth_number: Optional[str]
    surface: Optional[str]
    is_verified: bool = False


class ClassificationResponse(BaseModel):
    """Response model for classifications."""
    recording_uuid: str
    total_entities: int
    classifications: List[ClassificationItemResponse]
    summary: dict


class ClassifyTextRequest(BaseModel):
    """Request model for classifying arbitrary text."""
    text: str


@router.get("/{recording_uuid}", response_model=ClassificationResponse)
async def get_classifications(
    recording_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Get classifications for a recording's transcription."""
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

    # If no classifications exist yet, run classification
    if not transcription.classifications:
        classifications_result = classifier.classify(transcription.full_text)

        # Save classifications to database
        for cr in classifications_result:
            classification = Classification(
                transcription_id=transcription.id,
                category_id=1,  # Would need proper category lookup
                extracted_text=cr.extracted_text,
                normalized_value=cr.normalized_value,
                start_position=cr.start_position,
                end_position=cr.end_position,
                tooth_number=cr.tooth_number,
                surface=cr.surface,
                confidence_score=cr.confidence
            )
            db.add(classification)

        await db.commit()
        await db.refresh(transcription)

        classifications = classifications_result
    else:
        # Convert database records to response format
        classifications = [
            ClassificationResult(
                category=CategoryType(c.category.type.value) if c.category else CategoryType.OTHER,
                extracted_text=c.extracted_text,
                normalized_value=c.normalized_value,
                confidence=c.confidence_score,
                start_position=c.start_position or 0,
                end_position=c.end_position or 0,
                tooth_number=c.tooth_number,
                surface=c.surface
            )
            for c in transcription.classifications
        ]

    # Generate summary
    summary = classifier.get_summary(classifications)

    return ClassificationResponse(
        recording_uuid=recording_uuid,
        total_entities=len(classifications),
        classifications=[
            ClassificationItemResponse(
                id=None,
                category=c.category.value,
                extracted_text=c.extracted_text,
                normalized_value=c.normalized_value,
                confidence=c.confidence,
                tooth_number=c.tooth_number,
                surface=c.surface,
                is_verified=False
            )
            for c in classifications
        ],
        summary=summary
    )


@router.post("/classify-text", response_model=ClassificationResponse)
async def classify_text(request: ClassifyTextRequest):
    """
    Classify arbitrary dental text without storing.
    Useful for testing and preview.
    """
    classifications = classifier.classify(request.text)
    summary = classifier.get_summary(classifications)

    return ClassificationResponse(
        recording_uuid="preview",
        total_entities=len(classifications),
        classifications=[
            ClassificationItemResponse(
                id=None,
                category=c.category.value,
                extracted_text=c.extracted_text,
                normalized_value=c.normalized_value,
                confidence=c.confidence,
                tooth_number=c.tooth_number,
                surface=c.surface
            )
            for c in classifications
        ],
        summary=summary
    )


@router.post("/{recording_uuid}/{classification_id}/verify")
async def verify_classification(
    recording_uuid: str,
    classification_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Verify a classification as correct."""
    result = await db.execute(
        select(Classification).where(Classification.id == classification_id)
    )
    classification = result.scalar_one_or_none()

    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")

    classification.is_verified = True
    classification.verified_by_user_id = user_id
    from datetime import datetime
    classification.verified_at = datetime.utcnow()

    await db.commit()

    return {"status": "verified", "classification_id": classification_id}


@router.get("/categories")
async def get_categories():
    """Get all classification categories."""
    return {
        "categories": [
            {"type": ct.value, "name": ct.name, "description": _get_category_description(ct)}
            for ct in CategoryType
        ]
    }


def _get_category_description(category_type: CategoryType) -> str:
    """Get German description for a category type."""
    descriptions = {
        CategoryType.FINDING: "Befunde (z.B. Lockerungsgrad, Taschentiefe)",
        CategoryType.DIAGNOSIS: "Diagnosen (z.B. Karies, Parodontitis)",
        CategoryType.TREATMENT: "Behandlungsschritte (z.B. Wurzelkanalbehandlung)",
        CategoryType.MATERIAL: "Materialien (z.B. Composite, Amalgam)",
        CategoryType.INSTRUMENT: "Instrumente (z.B. Rosenbohrer, Scaler)",
        CategoryType.ANATOMY: "Anatomische Begriffe (z.B. Pulpa, Gingiva)",
        CategoryType.TOOTH: "Zahnbezeichnungen (FDI-Schema)",
        CategoryType.SURFACE: "Flächenbeschreibungen (z.B. mesial, distal)",
        CategoryType.OTHER: "Sonstige Begriffe",
    }
    return descriptions.get(category_type, "")
