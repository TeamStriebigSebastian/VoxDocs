"""
Audio recording database model.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class ProcessingStatus(str, enum.Enum):
    """Status of audio processing."""
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AudioRecording(Base):
    """Model for audio recordings."""

    __tablename__ = "audio_recordings"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)

    # File information
    original_filename = Column(String(255))
    encrypted_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer)
    duration_seconds = Column(Float)
    audio_format = Column(String(10), default="wav")

    # Recording metadata
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    recorded_by_user_id = Column(Integer, ForeignKey("users.id"))
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Processing status
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    error_message = Column(String(1000))

    # Retention
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    is_deleted = Column(Boolean, default=False)

    # Relationships
    practice = relationship("Practice", back_populates="recordings")
    room = relationship("Room", back_populates="recordings")
    recorded_by = relationship("User", back_populates="recordings")
    transcription = relationship("Transcription", back_populates="recording", uselist=False)

    def __repr__(self):
        return f"<AudioRecording(id={self.id}, uuid={self.uuid}, status={self.status})>"
