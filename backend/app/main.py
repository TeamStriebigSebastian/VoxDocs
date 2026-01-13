"""
VoxDocs - Dental Speech-to-Text Documentation System
Main FastAPI Application
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import asyncio

from app.core.config import settings, ensure_directories

# Ensure directories exist before anything else
ensure_directories()

from app.api import audio, transcription, classification, health, onboarding, export, appointments, webhooks
from app.core.database import init_db, get_db_session
from app.services.queue_service import queue_service, QueueJob
from app.services.whisper_service import whisper_service
from app.services.encryption_service import encryption_service
from app.services.llm_service import llm_service
from app.models.audio import AudioRecording
from app.models.transcription import Transcription, TranscriptionSegment
from app.models.task import Task, TaskPriority
from app.models.classification import Classification
from sqlalchemy import select
from datetime import datetime


# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
try:
    logger.add(
        "logs/voxdocs.log",
        rotation="10 MB",
        retention="90 days",
        compression="gz",
        level="DEBUG"
    )
except PermissionError:
    logger.warning("Could not create log file, logging to stdout only")


async def process_transcription_job(job: QueueJob) -> dict:
    """
    Process a transcription job from the queue.
    This function is called by the queue service to process pending jobs.
    """
    logger.info(f"Processing job {job.id} for recording {job.recording_id}")

    async with get_db_session() as db:
        try:
            # Get the recording
            result = await db.execute(
                select(AudioRecording).where(AudioRecording.id == job.recording_id)
            )
            recording = result.scalar_one_or_none()

            if not recording:
                raise Exception(f"Recording {job.recording_id} not found")

            # Decrypt the audio file
            encrypted_path = settings.ENCRYPTED_DIR / recording.encrypted_filename
            if not encrypted_path.exists():
                raise Exception(f"Encrypted file not found: {encrypted_path}")

            # Decrypt to temporary file
            decrypted_path = encryption_service.decrypt_file(encrypted_path)

            try:
                # Transcribe using Whisper with dental vocabulary boost
                # Run in thread pool to avoid blocking the event loop
                transcription_result = await asyncio.to_thread(
                    whisper_service.transcribe_with_dental_boost,
                    decrypted_path
                )

                # Update recording duration
                if transcription_result.segments:
                    recording.duration_seconds = transcription_result.segments[-1]["end"]

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

                await db.flush()

                # LLM-based correction, classification and task extraction
                if settings.USE_LLM_CORRECTION:
                    try:
                        logger.info(f"Running LLM analysis for transcription {transcription.id}")
                        llm_analysis = await llm_service.analyze_transcription(
                            transcription_result.text,
                            use_ollama=(settings.LLM_PROVIDER == "ollama")
                        )

                        # Update transcription with LLM results
                        transcription.corrected_text = llm_analysis.corrected_text
                        transcription.summary = llm_analysis.summary
                        transcription.llm_processed = datetime.utcnow()

                        # Create classifications from LLM
                        for cls in llm_analysis.classifications:
                            classification = Classification(
                                transcription_id=transcription.id,
                                category=cls.get("category", "other"),
                                text=cls.get("text", ""),
                                confidence=cls.get("confidence", 0.8)
                            )
                            db.add(classification)

                        # Create tasks from LLM
                        for task_data in llm_analysis.tasks:
                            priority_map = {
                                "hoch": TaskPriority.HIGH,
                                "mittel": TaskPriority.MEDIUM,
                                "niedrig": TaskPriority.LOW
                            }
                            task = Task(
                                transcription_id=transcription.id,
                                description=task_data.get("task", ""),
                                priority=priority_map.get(
                                    task_data.get("priority", "mittel"),
                                    TaskPriority.MEDIUM
                                ),
                                due_date=task_data.get("due", "nächster Termin")
                            )
                            db.add(task)

                        logger.info(f"LLM analysis completed: {len(llm_analysis.tasks)} tasks extracted")

                    except Exception as llm_error:
                        logger.warning(f"LLM analysis failed, continuing without: {llm_error}")

                # Update recording status
                recording.status = "completed"
                recording.processing_started_at = job.started_at
                recording.processing_completed_at = datetime.utcnow()

                await db.commit()

                logger.info(f"Transcription completed for job {job.id}")

                return {
                    "transcription_id": transcription.id,
                    "text_preview": transcription_result.text[:200] if transcription_result.text else "",
                    "processing_time": transcription_result.processing_time,
                    "llm_corrected": transcription.corrected_text is not None,
                    "tasks_extracted": len(llm_analysis.tasks) if settings.USE_LLM_CORRECTION else 0
                }

            finally:
                # Clean up decrypted file
                if decrypted_path.exists():
                    decrypted_path.unlink()

        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            # Update recording status to failed
            if recording:
                recording.status = "failed"
                recording.error_message = str(e)
                await db.commit()
            raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting VoxDocs Dental Speech-to-Text System...")
    await init_db()

    # Register the transcription processor with the queue service
    queue_service.set_processor(process_transcription_job)
    logger.info("Transcription processor registered")

    await queue_service.start()
    logger.info("VoxDocs started successfully")

    yield

    # Shutdown
    logger.info("Shutting down VoxDocs...")
    await queue_service.stop()
    logger.info("VoxDocs shut down complete")


app = FastAPI(
    title="VoxDocs - Dental Speech-to-Text",
    description="GDPR-compliant speech recognition system for German dental practices",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration for PWA
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(audio.router, prefix="/api/audio", tags=["Audio"])
app.include_router(transcription.router, prefix="/api/transcription", tags=["Transcription"])
app.include_router(classification.router, prefix="/api/classification", tags=["Classification"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(appointments.router, tags=["Appointments"])
app.include_router(webhooks.router, tags=["Webhooks"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "VoxDocs",
        "version": "1.0.0",
        "description": "Dental Speech-to-Text Documentation System"
    }
