"""
API endpoints for nursing care appointments.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
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
    db: Session = Depends(get_db)
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
        db.commit()
        db.refresh(appointment)

        logger.info(f"Created appointment {appointment_uuid}")

        return {
            "uuid": appointment_uuid,
            "id": appointment.id,
            "status": appointment.status.value
        }

    except Exception as e:
        logger.error(f"Error creating appointment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_uuid}/upload-audio")
async def upload_audio(
    appointment_uuid: str,
    practice_id: int = Form(...),
    audio_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload an audio recording to an appointment."""
    try:
        # Find appointment
        appointment = db.query(Appointment).filter(
            Appointment.uuid == appointment_uuid
        ).first()

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
        db.commit()
        db.refresh(audio_recording)

        logger.info(f"Uploaded audio {audio_uuid} to appointment {appointment_uuid}")

        return {
            "audio_uuid": audio_uuid,
            "appointment_uuid": appointment_uuid
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading audio: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_uuid}/upload-photo")
async def upload_photo(
    appointment_uuid: str,
    photo_file: UploadFile = File(...),
    caption: str = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a photo to an appointment."""
    try:
        # Find appointment
        appointment = db.query(Appointment).filter(
            Appointment.uuid == appointment_uuid
        ).first()

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
        db.commit()
        db.refresh(photo)

        logger.info(f"Uploaded photo {photo_uuid} to appointment {appointment_uuid}")

        return {
            "photo_uuid": photo_uuid,
            "appointment_uuid": appointment_uuid
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading photo: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_uuid}/complete")
async def complete_appointment(
    appointment_uuid: str,
    db: Session = Depends(get_db)
):
    """
    Complete an appointment and trigger transcription processing.
    """
    try:
        appointment = db.query(Appointment).filter(
            Appointment.uuid == appointment_uuid
        ).first()

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
        db.commit()
        db.refresh(appointment)

        # Trigger async processing (background task)
        # This will be picked up by a worker or done immediately
        logger.info(f"Completed appointment {appointment_uuid}, starting transcription")

        # Start processing in background
        import asyncio
        asyncio.create_task(process_appointment_transcription(appointment.id, db))

        return {
            "uuid": appointment_uuid,
            "status": appointment.status.value,
            "message": "Appointment completed, transcription starting"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error completing appointment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{appointment_uuid}")
async def get_appointment(
    appointment_uuid: str,
    db: Session = Depends(get_db)
):
    """Get appointment details with all recordings, photos, and transcription."""
    try:
        appointment = db.query(Appointment).filter(
            Appointment.uuid == appointment_uuid
        ).first()

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Build response
        response = {
            "uuid": appointment.uuid,
            "patient_name": appointment.patient_name,
            "started_at": appointment.started_at.isoformat(),
            "completed_at": appointment.completed_at.isoformat() if appointment.completed_at else None,
            "status": appointment.status.value,
            "audio_recordings": [
                {
                    "uuid": audio.uuid,
                    "duration": audio.duration_seconds,
                    "recorded_at": audio.recorded_at.isoformat()
                }
                for audio in appointment.audio_recordings
            ],
            "photos": [
                {
                    "uuid": photo.uuid,
                    "caption": photo.caption,
                    "taken_at": photo.taken_at.isoformat()
                }
                for photo in appointment.photos
            ],
            "transcription": None
        }

        # Add transcription if available
        if appointment.transcription:
            trans = appointment.transcription
            response["transcription"] = {
                "status": trans.status.value,
                "summary": trans.summary,
                "services": trans.services,
                "observations": trans.observations,
                "next_tasks": trans.next_tasks,
                "tts_audio_url": trans.tts_audio_url,
                "confirmed_at": trans.confirmed_at.isoformat() if trans.confirmed_at else None
            }

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{appointment_uuid}/confirm")
async def confirm_appointment(
    appointment_uuid: str,
    confirmed_by: str = Form(...),
    db: Session = Depends(get_db)
):
    """Confirm the appointment documentation by the caregiver."""
    try:
        appointment = db.query(Appointment).filter(
            Appointment.uuid == appointment_uuid
        ).first()

        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")

        # Update appointment
        appointment.status = AppointmentStatus.CONFIRMED
        appointment.confirmed_at = datetime.utcnow()
        appointment.confirmed_by = confirmed_by

        # Update transcription
        if appointment.transcription:
            appointment.transcription.status = TranscriptionStatus.CONFIRMED
            appointment.transcription.confirmed_at = datetime.utcnow()
            appointment.transcription.confirmed_by = confirmed_by

        db.commit()

        logger.info(f"Confirmed appointment {appointment_uuid} by {confirmed_by}")

        return {
            "uuid": appointment_uuid,
            "status": "confirmed",
            "confirmed_at": appointment.confirmed_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error confirming appointment: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_appointments(
    practice_id: int,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List appointments for a practice."""
    try:
        query = db.query(Appointment).filter(Appointment.practice_id == practice_id)

        if status:
            query = query.filter(Appointment.status == status)

        appointments = query.order_by(Appointment.started_at.desc()).limit(limit).all()

        return [
            {
                "uuid": appt.uuid,
                "patient_name": appt.patient_name,
                "started_at": appt.started_at.isoformat(),
                "status": appt.status.value,
                "audio_count": len(appt.audio_recordings),
                "photo_count": len(appt.photos)
            }
            for appt in appointments
        ]

    except Exception as e:
        logger.error(f"Error listing appointments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_appointment_transcription(appointment_id: int, db: Session):
    """
    Background task to process appointment transcription.
    This combines all audio recordings and generates the nursing documentation.
    """
    try:
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if not appointment or not appointment.transcription:
            return

        transcription = appointment.transcription
        transcription.status = TranscriptionStatus.PROCESSING
        db.commit()

        # Transcribe all audio recordings
        all_text = []
        for audio in appointment.audio_recordings:
            # Decrypt and transcribe
            from app.services.encryption_service import decrypt_file
            decrypted_audio = await decrypt_file(audio.encrypted_filename)

            # Use Whisper to transcribe
            result = await whisper_service.transcribe_audio(decrypted_audio)
            all_text.append(result['text'])

        # Combine all transcriptions
        full_text = " ".join(all_text)
        transcription.full_text = full_text

        # Analyze with LLM
        analysis = await nursing_llm_service.analyze_transcription(full_text)

        transcription.summary = analysis.summary
        transcription.services = analysis.services
        transcription.observations = analysis.observations
        transcription.next_tasks = analysis.next_tasks

        # Generate TTS audio
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

        db.commit()

        logger.info(f"Completed transcription for appointment {appointment.uuid}")

        # Send webhook notification
        from app.api.webhooks import send_transcription_ready_notification
        await send_transcription_ready_notification(appointment.uuid)

    except Exception as e:
        logger.error(f"Error processing appointment transcription: {e}")
        if transcription:
            transcription.status = TranscriptionStatus.ERROR
            db.commit()


@router.get("/{appointment_uuid}/tts-audio")
async def get_tts_audio(
    appointment_uuid: str,
    db: Session = Depends(get_db)
):
    """Get the generated TTS audio file for an appointment."""
    try:
        appointment = db.query(Appointment).filter(
            Appointment.uuid == appointment_uuid
        ).first()

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting TTS audio: {e}")
        raise HTTPException(status_code=500, detail=str(e))
