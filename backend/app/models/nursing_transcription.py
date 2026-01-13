"""
Nursing transcription model with care-specific categories.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class TranscriptionStatus(str, enum.Enum):
    """Status of nursing transcription processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    CONFIRMED = "confirmed"
    ERROR = "error"


class NursingTranscription(Base):
    """Model for nursing care transcription with specialized categories."""

    __tablename__ = "nursing_transcriptions"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), unique=True, nullable=False)

    # Raw transcription
    full_text = Column(Text, nullable=False)
    language = Column(String(10), default="de")

    # Nursing care categories
    summary = Column(Text)  # Gesamte Aufnahme/Zusammenfassung
    services = Column(Text)  # Erbrachte Leistungen (Körperpflege, Mobilisation, Medikamentengabe)
    observations = Column(Text)  # Besonderheiten
    next_tasks = Column(Text)  # Aufgaben für nächsten Termin

    # TTS Audio
    tts_audio_url = Column(String(500))  # URL to generated TTS audio
    tts_audio_filename = Column(String(255))
    tts_generated_at = Column(DateTime)

    # Processing metadata
    whisper_model = Column(String(50))
    processing_time_seconds = Column(Float)
    confidence_score = Column(Float)

    # Status
    status = Column(Enum(TranscriptionStatus), default=TranscriptionStatus.PENDING)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processed_at = Column(DateTime)

    # Confirmation
    confirmed_at = Column(DateTime)
    confirmed_by = Column(String(255))

    # Relationships
    appointment = relationship("Appointment", back_populates="transcription")

    def __repr__(self):
        return f"<NursingTranscription(id={self.id}, appointment_id={self.appointment_id}, status={self.status})>"
