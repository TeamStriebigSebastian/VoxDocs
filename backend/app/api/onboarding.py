"""
Onboarding API endpoints for phrase recording.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from loguru import logger
import aiofiles
import uuid

from app.core.config import settings
from app.core.database import get_db
from app.models.onboarding import OnboardingSession, OnboardingStatus, PhraseRecording, PhraseCategory
from app.services.encryption_service import encryption_service

router = APIRouter()


# Dental phrases for onboarding organized by category
DENTAL_PHRASES = {
    PhraseCategory.TOOTH_DESIGNATION: [
        "Zahn eins eins", "Zahn eins zwei", "Zahn eins drei", "Zahn eins vier",
        "Zahn eins fünf", "Zahn eins sechs", "Zahn eins sieben", "Zahn eins acht",
        "Zahn zwei eins", "Zahn zwei zwei", "Zahn zwei drei", "Zahn zwei vier",
        "Zahn zwei fünf", "Zahn zwei sechs", "Zahn zwei sieben", "Zahn zwei acht",
        "Zahn drei eins", "Zahn drei zwei", "Zahn drei drei", "Zahn drei vier",
        "Zahn drei fünf", "Zahn drei sechs", "Zahn drei sieben", "Zahn drei acht",
        "Zahn vier eins", "Zahn vier zwei", "Zahn vier drei", "Zahn vier vier",
        "Zahn vier fünf", "Zahn vier sechs", "Zahn vier sieben", "Zahn vier acht",
        "Quadrant eins", "Quadrant zwei", "Quadrant drei", "Quadrant vier",
        "Oberkiefer rechts", "Oberkiefer links", "Unterkiefer rechts", "Unterkiefer links",
    ],
    PhraseCategory.SURFACE: [
        "mesial", "distal", "bukkal", "palatinal", "okklusal",
        "vestibulär", "oral", "inzisal", "approximal", "zervikal", "koronal", "lingual",
        "mesio-okklusal", "disto-okklusal", "mesio-disto-okklusal",
        "bukko-mesial", "bukko-distal", "palatino-mesial", "palatino-distal",
    ],
    PhraseCategory.DIAGNOSIS: [
        "Karies Grad eins", "Karies Grad zwei", "Karies Grad drei", "Karies Grad vier",
        "Karies profunda", "Karies media", "Karies superficialis",
        "Parodontitis apicalis chronica", "Parodontitis apicalis acuta",
        "Pulpitis reversibel", "Pulpitis irreversibel",
        "Gingivitis", "Periimplantitis", "Wurzelkaries",
        "Abrasion", "Erosion", "Attrition", "Dentinhypersensibilität",
    ],
    PhraseCategory.FINDING: [
        "Lockerungsgrad eins", "Lockerungsgrad zwei", "Lockerungsgrad drei",
        "Taschentiefe drei Millimeter", "Taschentiefe vier Millimeter",
        "Taschentiefe fünf Millimeter", "Taschentiefe sechs Millimeter",
        "Blutung auf Sondierung", "Blutung auf Sondierung positiv",
        "Furkationsbefall Grad eins", "Furkationsbefall Grad zwei", "Furkationsbefall Grad drei",
        "Fistel", "Schwellung", "Rezession zwei Millimeter", "Rezession drei Millimeter",
        "Sensibilität positiv", "Sensibilität negativ", "Sensibilität vermindert",
        "Perkussion positiv", "Perkussion negativ", "Perkussion schmerzhaft",
    ],
    PhraseCategory.TREATMENT: [
        "Wurzelkanalbehandlung", "Kavitätenpräparation", "Composite-Füllung",
        "Amalgam-Füllung", "Kronenversorgung", "Brückenversorgung",
        "Extraktion", "Implantation", "Professionelle Zahnreinigung",
        "Scaling", "Wurzelglättung", "Naht", "Inzision", "Drainage",
        "Wurzelspitzenresektion", "Hemisektion", "Prämolarisierung",
        "Stiftaufbau", "Inlay-Präparation", "Onlay-Präparation",
    ],
    PhraseCategory.MATERIAL: [
        "Composite", "Amalgam", "Glasionomerzement",
        "Zirkonoxid-Krone", "Keramik-Krone", "Metallkeramik-Krone",
        "Titan-Implantat", "Guttapercha", "MTA",
        "Artikain", "Lidocain", "Mepivacain",
        "Calciumhydroxid", "Eugenol", "Phosphatzement",
        "Flowable Composite", "Bulk-Fill Composite",
    ],
    PhraseCategory.INSTRUMENT: [
        "Rosenbohrer", "Fissurenbohrer", "Diamantschleifer",
        "H-Feile", "K-Feile", "Reamers",
        "Scaler", "Kürette", "Gracey-Kürette",
        "Exkavator", "Stopfer", "Heidemannspatel",
        "Sonde", "Parodontalsonde", "Pinzette",
        "Matrizenband", "Keil", "Artikulationspapier",
    ],
    PhraseCategory.ANATOMY: [
        "Schmelz", "Dentin", "Pulpa", "Zement",
        "Parodontalspalt", "Alveolarknochen", "Lamina dura",
        "Gingiva", "Sulkus", "Papille",
        "Apex", "Bifurkation", "Trifurkation", "Foramen apicale",
        "Wurzelkanal", "Pulpakammer", "Kronenpulpa",
        "Schmelz-Zement-Grenze", "Zahnhals",
    ],
    PhraseCategory.SENTENCE: [
        "Zahn eins sechs mesial Karies Grad zwei",
        "Zahn zwei sieben distal Composite-Füllung",
        "Taschentiefe sechs Millimeter distal an Zahn zwei sieben",
        "Extraktion von Zahn drei acht indiziert",
        "Zahn vier sechs Wurzelkanalbehandlung notwendig",
        "Lockerungsgrad zwei an Zahn drei eins",
        "Blutung auf Sondierung positiv mesial Zahn eins sechs",
        "Karies profunda an Zahn vier sechs mit Pulpabeteiligung",
        "Fistel bukkal Zahn zwei sechs",
        "Rezession drei Millimeter vestibulär Zahn drei drei",
        "Furkationsbefall Grad zwei an Zahn drei sechs",
        "Sensibilität negativ an Zahn eins eins",
        "Gingivitis generalisiert im Unterkiefer",
        "Periimplantitis regio zwei sechs",
        "Kronenversorgung Zahn vier fünf geplant",
    ],
}


class OnboardingSessionResponse(BaseModel):
    """Response model for onboarding session."""
    id: int
    status: str
    total_phrases: int
    completed_phrases: int
    current_category: Optional[str]
    progress_percentage: float
    started_at: Optional[datetime]


class PhraseResponse(BaseModel):
    """Response model for a phrase to record."""
    phrase_index: int
    phrase_text: str
    category: str
    is_recorded: bool


class CategoryProgressResponse(BaseModel):
    """Response model for category progress."""
    category: str
    total_phrases: int
    completed_phrases: int
    phrases: List[PhraseResponse]


@router.post("/start", response_model=OnboardingSessionResponse)
async def start_onboarding(
    practice_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Start a new onboarding session."""
    # Calculate total phrases
    total_phrases = sum(len(phrases) for phrases in DENTAL_PHRASES.values())

    # Create session
    session = OnboardingSession(
        practice_id=practice_id,
        user_id=user_id,
        status=OnboardingStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
        total_phrases=total_phrases,
        current_category=PhraseCategory.TOOTH_DESIGNATION
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(f"Onboarding session started: {session.id} for user {user_id}")

    return OnboardingSessionResponse(
        id=session.id,
        status=session.status.value,
        total_phrases=session.total_phrases,
        completed_phrases=0,
        current_category=session.current_category.value if session.current_category else None,
        progress_percentage=0.0,
        started_at=session.started_at
    )


@router.get("/{session_id}", response_model=OnboardingSessionResponse)
async def get_session_status(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding session status."""
    result = await db.execute(
        select(OnboardingSession)
        .options(selectinload(OnboardingSession.phrase_recordings))
        .where(OnboardingSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    progress = (session.completed_phrases / session.total_phrases * 100) if session.total_phrases > 0 else 0

    return OnboardingSessionResponse(
        id=session.id,
        status=session.status.value,
        total_phrases=session.total_phrases,
        completed_phrases=session.completed_phrases,
        current_category=session.current_category.value if session.current_category else None,
        progress_percentage=progress,
        started_at=session.started_at
    )


@router.get("/{session_id}/phrases", response_model=List[CategoryProgressResponse])
async def get_phrases(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all phrases organized by category with recording status."""
    result = await db.execute(
        select(OnboardingSession)
        .options(selectinload(OnboardingSession.phrase_recordings))
        .where(OnboardingSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get recorded phrases
    recorded_phrases = {
        (pr.category.value, pr.phrase_index): True
        for pr in session.phrase_recordings
    }

    # Build response
    categories = []
    for category, phrases in DENTAL_PHRASES.items():
        phrase_list = []
        completed = 0
        for idx, phrase in enumerate(phrases):
            is_recorded = (category.value, idx) in recorded_phrases
            if is_recorded:
                completed += 1
            phrase_list.append(PhraseResponse(
                phrase_index=idx,
                phrase_text=phrase,
                category=category.value,
                is_recorded=is_recorded
            ))

        categories.append(CategoryProgressResponse(
            category=category.value,
            total_phrases=len(phrases),
            completed_phrases=completed,
            phrases=phrase_list
        ))

    return categories


@router.post("/{session_id}/record")
async def record_phrase(
    session_id: int,
    file: UploadFile = File(...),
    category: str = Form(...),
    phrase_index: int = Form(...),
    phrase_text: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload a phrase recording."""
    result = await db.execute(
        select(OnboardingSession).where(OnboardingSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != OnboardingStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Session is not in progress")

    # Validate category
    try:
        phrase_category = PhraseCategory(category)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid category")

    # Save and encrypt file
    recording_uuid = str(uuid.uuid4())
    temp_path = settings.AUDIO_DIR / f"onboarding_{recording_uuid}.wav"

    async with aiofiles.open(temp_path, 'wb') as f:
        content = await file.read()
        await f.write(content)

    # Encrypt
    encrypted_filename = f"onboarding_{recording_uuid}.enc"
    encrypted_path = settings.ENCRYPTED_DIR / encrypted_filename
    encryption_service.encrypt_file(temp_path, encrypted_path)
    temp_path.unlink()

    # Create phrase recording
    phrase_recording = PhraseRecording(
        session_id=session_id,
        phrase_text=phrase_text,
        category=phrase_category,
        phrase_index=phrase_index,
        encrypted_filename=encrypted_filename,
        recorded_at=datetime.utcnow()
    )

    db.add(phrase_recording)

    # Update session progress
    session.completed_phrases += 1

    # Check if category is complete
    category_phrases = DENTAL_PHRASES.get(phrase_category, [])
    if phrase_index == len(category_phrases) - 1:
        # Move to next category
        categories = list(DENTAL_PHRASES.keys())
        current_idx = categories.index(phrase_category)
        if current_idx < len(categories) - 1:
            session.current_category = categories[current_idx + 1]

    # Check if all phrases are complete
    if session.completed_phrases >= session.total_phrases:
        session.status = OnboardingStatus.COMPLETED
        session.completed_at = datetime.utcnow()
        actual_duration = (session.completed_at - session.started_at).total_seconds() / 60
        session.actual_duration_minutes = actual_duration
        logger.info(f"Onboarding completed: {session_id} in {actual_duration:.1f} minutes")

    await db.commit()

    return {
        "status": "recorded",
        "phrase_index": phrase_index,
        "category": category,
        "completed_phrases": session.completed_phrases,
        "total_phrases": session.total_phrases,
        "session_status": session.status.value
    }


@router.get("/phrases/all")
async def get_all_phrases():
    """Get all dental phrases for reference."""
    result = {}
    for category, phrases in DENTAL_PHRASES.items():
        result[category.value] = {
            "name": _get_category_name(category),
            "phrases": phrases
        }
    return result


def _get_category_name(category: PhraseCategory) -> str:
    """Get German name for a category."""
    names = {
        PhraseCategory.TOOTH_DESIGNATION: "Zahnbezeichnungen",
        PhraseCategory.SURFACE: "Flächenbeschreibungen",
        PhraseCategory.DIAGNOSIS: "Diagnosen",
        PhraseCategory.FINDING: "Befunde",
        PhraseCategory.TREATMENT: "Behandlungsschritte",
        PhraseCategory.MATERIAL: "Materialien",
        PhraseCategory.INSTRUMENT: "Instrumente",
        PhraseCategory.ANATOMY: "Anatomische Begriffe",
        PhraseCategory.SENTENCE: "Satzkombinationen",
    }
    return names.get(category, category.value)
