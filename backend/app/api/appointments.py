"""
API endpoints for nursing care appointments.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from loguru import logger

from app.core.database import get_db
from app.models import (
    Appointment, AppointmentStatus,
    AudioRecording, Photo,
    NursingTranscription, TranscriptionStatus
)
from app.services.encryption_service import encrypt_file
from app.services.whisper_service import whisper_service
from app.services.nursing_llm_service import nursing_llm_service
from app.services.piper_tts_service import piper_tts_service


router = APIRouter(prefix="/api/appointments", tags=["appointments"])


@router.post("/create")
async def create_appointment(
    practice_id: int = Form(...),
    patient_name: str = Form(None),
    patient_id: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Create a new nursing care appointment."""
    try:
        appointment_uuid = str(uuid.uuid4())

        appointment = Appointment(
            uuid=appointment_uuid,
            practice_id=practice_id,
            patient_name=patient_name,
            patient_id=patient_id,
            started_at=datetime.utcnow(),
            status=AppointmentStatus.IN_PROGRESS
        )

        db.add(appointment)
        await db.commit()
        await db.refresh(appointment)

        logger.info(f"Created appointment {appointment_uuid}")

        return {
            "uuid": appointment_uuid,
            "id": appointment.id,
            "status": appointment.status.value
        }

    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_uuid}/upload-audio")
async def upload_audio(
    appointment_uuid: str,
    practice_id: int = Form(...),
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload an audio recording to an appointment."""
    try:
        # Find appointment
        result = await db.execute(select(Appointment).where(Appointment.uuid == appointment_uuid))
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Read and encrypt audio
        audio_data = await audio_file.read()
        encrypted_filename, file_size = await encrypt_file(
            audio_data,
            f"appointment_{appointment_uuid}_{uuid.uuid4()}.wav"
        )

        # Create audio recording
        audio_uuid = str(uuid.uuid4())
        audio_recording = AudioRecording(
            uuid=audio_uuid,
            practice_id=practice_id,
            appointment_id=appointment.id,
            original_filename=audio_file.filename,
            encrypted_filename=encrypted_filename,
            file_size_bytes=file_size,
            recorded_at=datetime.utcnow()
        )

        db.add(audio_recording)
        await db.commit()
        await db.refresh(audio_recording)

        logger.info(f"Uploaded audio {audio_uuid} to appointment {appointment_uuid}")

        return {
            "audio_uuid": audio_uuid,
            "appointment_uuid": appointment_uuid
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_uuid}/upload-photo")
async def upload_photo(
    appointment_uuid: str,
    photo_file: UploadFile = File(...),
    caption: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Upload a photo to an appointment."""
    try:
        # Find appointment
        result = await db.execute(select(Appointment).where(Appointment.uuid == appointment_uuid))
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Read and encrypt photo
        photo_data = await photo_file.read()
        encrypted_filename, file_size = await encrypt_file(
            photo_data,
            f"photo_{appointment_uuid}_{uuid.uuid4()}.jpg"
        )

        # Create photo record
        photo_uuid = str(uuid.uuid4())
        photo = Photo(
            uuid=photo_uuid,
            appointment_id=appointment.id,
            original_filename=photo_file.filename,
            encrypted_filename=encrypted_filename,
            file_size_bytes=file_size,
            caption=caption,
            mime_type=photo_file.content_type or "image/jpeg",
            taken_at=datetime.utcnow()
        )

        db.add(photo)
        await db.commit()
        await db.refresh(photo)

        logger.info(f"Uploaded photo {photo_uuid} to appointment {appointment_uuid}")

        return {
            "photo_uuid": photo_uuid,
            "appointment_uuid": appointment_uuid
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading photo: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_uuid}/complete")
async def complete_appointment(
    appointment_uuid: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Complete an appointment and trigger transcription processing.
    """
    try:
        result = await db.execute(select(Appointment).where(Appointment.uuid == appointment_uuid))
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Update appointment status
        appointment.status = AppointmentStatus.COMPLETED
        appointment.completed_at = datetime.utcnow()

        # Create transcription record
        transcription = NursingTranscription(
            appointment_id=appointment.id,
            full_text="",
            status=TranscriptionStatus.PENDING
        )

        db.add(transcription)
        await db.commit()
        await db.refresh(appointment)

        # Trigger async processing (background task)
        # This will be picked up by a worker or done immediately
        logger.info(f"Completed appointment {appointment_uuid}, starting transcription")

        # Start processing in background using FastAPI's BackgroundTasks or custom solution
        # Since we need a fresh DB session for the background task, we'll pass the ID
        background_tasks.add_task(run_background_transcription, appointment.id)

        return {
            "uuid": appointment_uuid,
            "status": appointment.status.value,
            "message": "Appointment completed, transcription starting"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing appointment: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


async def run_background_transcription(appointment_id: int):
    """Helper to run the transcription with a new session"""
    logger.info(f"STARTING BACKGROUND TASK for appointment_id={appointment_id}")
    try:
        from app.core.database import get_db_session
        async with get_db_session() as db:
            logger.info("Background DB session established")
            await process_appointment_transcription(appointment_id, db)
    except Exception as e:
        logger.error(f"FATAL BACKGROUND ERROR: {e}")
        import traceback
        logger.error(traceback.format_exc())


from sqlalchemy.orm import selectinload

async def process_appointment_transcription(appointment_id: int, db: AsyncSession):
    """
    Background task to process appointment transcription.
    This combines all audio recordings and generates the nursing documentation.
    """
    logger.info(f"Processing transcription logic for {appointment_id}")
    try:
        # Load appointment with all needed relationships
        query = select(Appointment).where(Appointment.id == appointment_id).options(
            selectinload(Appointment.transcription),
            selectinload(Appointment.audio_recordings)
        )
        result = await db.execute(query)
        appointment = result.scalar_one_or_none()
        
        if not appointment:
            logger.error(f"Appointment {appointment_id} not found in background task")
            return
            
        if not appointment.transcription:
            logger.error(f"Appointment {appointment_id} has no transcription record")
            return

        logger.info(f"Found appointment {appointment.uuid}, status: {appointment.transcription.status}")

        transcription = appointment.transcription
        transcription.status = TranscriptionStatus.PROCESSING
        await db.commit()

        # Transcribe all audio recordings
        all_text = []
        logger.info(f"Processing {len(appointment.audio_recordings)} audio files")
        
        for audio in appointment.audio_recordings:
            logger.info(f"Decrypting audio {audio.uuid}")
            # Decrypt and transcribe
            from app.services.encryption_service import decrypt_file
            decrypted_audio = await decrypt_file(audio.encrypted_filename)

            logger.info(f"Transcribing audio {audio.uuid}")
            
            # Write decrypted bytes to a temp file for Whisper to read
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(decrypted_audio)
                tmp_path = tmp_file.name
            
            try:
                # Use Whisper to transcribe (blocking call run in executor)
                import asyncio
                from pathlib import Path
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    None, 
                    lambda: whisper_service.transcribe(Path(tmp_path))
                )
                
                text = result.text
                logger.info(f"Transcription result: {text[:50]}...")
                all_text.append(text)
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        # Combine all transcriptions
        full_text = " ".join(all_text)
        transcription.full_text = full_text
        
        # Determine language (use the last detected one or default)
        # Note: Whisper returns language in 'info' object which we haven't been capturing fully in the loop
        # For MVP, we'll assume the LLM detects it or we rely on 'de' default if not set
        # Actually, let's update the loop to capture detected language from the last segment
        # But `whisper_service.transcribe` returns `TranscriptionResult` which has .language
        
        # We need to capture it in the loop. Let's assume strict single-speaker/single-language per appointment for now
        # The last result's language is a decent proxy
        if 'result' in locals() and hasattr(result, 'language'):
             transcription.original_language = result.language
             logger.info(f"Detected language: {result.language}")
        
        logger.info(f"Full text length: {len(full_text)}")


        # Analyze with LLM
        logger.info("Starting LLM analysis")
        analysis = await nursing_llm_service.analyze_transcription(full_text)
        logger.info("LLM analysis complete")

        transcription.translated_text = analysis.corrected_text  # LLM returns German text in 'corrected_text'
        transcription.summary = analysis.summary
        transcription.services = analysis.services
        transcription.observations = analysis.observations
        transcription.next_tasks = analysis.next_tasks

        # Generate TTS audio
        logger.info("Generating TTS audio")
        tts_path = await piper_tts_service.generate_nursing_documentation_audio(
            analysis.summary,
            analysis.services,
            analysis.observations,
            analysis.next_tasks,
            appointment.uuid
        )

        if tts_path:
            transcription.tts_audio_url = f"/api/appointments/{appointment.uuid}/tts-audio"
            transcription.tts_audio_filename = tts_path
            transcription.tts_generated_at = datetime.utcnow()

        transcription.status = TranscriptionStatus.READY
        transcription.processed_at = datetime.utcnow()

        await db.commit()

        logger.info(f"SUCCESS: Completed transcription for appointment {appointment.uuid}")

        # Send webhook notification
        from app.api.webhooks import send_transcription_ready_notification
        await send_transcription_ready_notification(appointment.uuid)

    except Exception as e:
        logger.error(f"Error processing appointment transcription: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        if 'transcription' in locals() and transcription:
            transcription.status = TranscriptionStatus.ERROR
            await db.commit()



@router.get("/{appointment_uuid}/tts-audio")
async def get_tts_audio(
    appointment_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Get the generated TTS audio file for an appointment."""
    try:
        from sqlalchemy.orm import selectinload
        query = select(Appointment).where(Appointment.uuid == appointment_uuid).options(
            selectinload(Appointment.transcription)
        )
        result = await db.execute(query)
        appointment = result.scalar_one_or_none()

        if not appointment or not appointment.transcription:
            raise HTTPException(status_code=404, detail="Appointment or transcription not found")

        transcription = appointment.transcription

        if not transcription.tts_audio_filename:
            raise HTTPException(status_code=404, detail="TTS audio not generated yet")

        return FileResponse(
            transcription.tts_audio_filename,
            media_type="audio/wav",
            filename=f"appointment_{appointment_uuid}.wav"
        )

    except Exception as e:
        logger.error(f"Error getting TTS audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[dict])
async def list_appointments(
    practice_id: int,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List appointments for a practice with optional status filter."""
    try:
        from sqlalchemy import func
        
        # Build query
        query = select(Appointment).where(Appointment.practice_id == practice_id)
        
        if status and status != 'all':
            query = query.where(Appointment.status == status)
            
        # Order by most recent first
        query = query.order_by(Appointment.started_at.desc())
        
        # Execute
        result = await db.execute(query.options(
            selectinload(Appointment.audio_recordings),
            selectinload(Appointment.photos)
        ))
        appointments = result.scalars().all()
        
        # Transform to summary format
        summary_list = []
        for appt in appointments:
            summary_list.append({
                "uuid": appt.uuid,
                "patient_name": appt.patient_name,
                "started_at": appt.started_at,
                "status": appt.status.value,
                "audio_count": len(appt.audio_recordings),
                "photo_count": len(appt.photos)
            })
            
        return summary_list

    except Exception as e:
        logger.error(f"Error listing appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{appointment_uuid}")
async def get_appointment(
    appointment_uuid: str,
    db: AsyncSession = Depends(get_db)
):
    """Get clear details for a single appointment."""
    try:
        query = select(Appointment).where(Appointment.uuid == appointment_uuid).options(
            selectinload(Appointment.audio_recordings),
            selectinload(Appointment.photos),
            selectinload(Appointment.transcription)
        )
        
        result = await db.execute(query)
        appointment = result.scalar_one_or_none()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        # Manually construct response to ensure clean JSON structure
        # (Alternatively use Pydantic models, but this is quicker for direct matching)
        response = {
            "uuid": appointment.uuid,
            "patient_name": appointment.patient_name,
            "started_at": appointment.started_at,
            "completed_at": appointment.completed_at,
            "status": appointment.status.value,
            "audio_recordings": [
                {
                    "uuid": a.uuid,
                    "duration": a.duration_seconds, # Assuming model has this or calculates it
                    "recorded_at": a.recorded_at
                } for a in appointment.audio_recordings
            ],
            "photos": [
                {
                    "uuid": p.uuid,
                    "caption": p.caption,
                    "taken_at": p.taken_at
                } for p in appointment.photos
            ],
            "transcription": None
        }
        
        if appointment.transcription:
            t = appointment.transcription
            response["transcription"] = {
                "status": t.status.value,
                "summary": t.summary,
                "full_text": t.full_text,
                "translated_text": t.translated_text,
                "original_language": t.original_language,
                "services": t.services,
                "observations": t.observations,
                "next_tasks": t.next_tasks,
                "tts_audio_url": t.tts_audio_url,
                "confirmed_at": t.confirmed_at
            }
            
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{appointment_uuid}/transcription")
async def update_transcription(
    appointment_uuid: str,
    summary: str = Form(None),
    services: str = Form(None),
    observations: str = Form(None),
    next_tasks: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Update transcription details (manual correction)."""
    try:
        query = select(Appointment).where(Appointment.uuid == appointment_uuid).options(
            selectinload(Appointment.transcription)
        )
        result = await db.execute(query)
        appointment = result.scalar_one_or_none()

        if not appointment or not appointment.transcription:
            raise HTTPException(status_code=404, detail="Appointment or transcription not found")

        # Update fields if provided
        t = appointment.transcription
        if summary is not None:
            t.summary = summary
        if services is not None:
            t.services = services
        if observations is not None:
            t.observations = observations
        if next_tasks is not None:
            t.next_tasks = next_tasks

        # Mark as manual edit? Maybe status stays 'ready'.
        
        await db.commit()
        
        logger.info(f"Updated transcription for {appointment_uuid}")
        
        return {"status": "updated", "uuid": appointment_uuid}

    except Exception as e:
        logger.error(f"Error updating transcription: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{appointment_uuid}/confirm")
async def confirm_appointment(
    appointment_uuid: str,
    confirmed_by: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Confirm an appointment documentation."""
    try:
        query = select(Appointment).where(Appointment.uuid == appointment_uuid).options(
            selectinload(Appointment.transcription)
        )
        result = await db.execute(query)
        appointment = result.scalar_one_or_none()

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
            
        if not appointment.transcription:
             raise HTTPException(status_code=400, detail="No transcription to confirm")

        # Update status
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.transcription.status = TranscriptionStatus.CONFIRMED
        appointment.transcription.confirmed_at = datetime.utcnow()
        # In a real app we'd store confirmed_by user ID too
        
        await db.commit()
        
        logger.info(f"Confirmed appointment {appointment_uuid} by {confirmed_by}")
        
        return {"status": "confirmed"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming appointment: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
