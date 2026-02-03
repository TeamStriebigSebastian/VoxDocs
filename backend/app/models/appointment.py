"""
Appointment model for nursing care visits.
A single appointment can have multiple audio recordings and photos.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AppointmentStatus(str, enum.Enum):
    """Status of a nursing care appointment."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"


class Appointment(Base):
    """Model for nursing care appointments."""

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)

    # Patient information
    patient_name = Column(String(255))
    patient_id = Column(String(100))  # External patient ID if available

    # Appointment details
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    caregiver_id = Column(Integer, ForeignKey("users.id"))  # The nurse/caregiver

    # Timing
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    # Status
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.IN_PROGRESS)

    # Confirmation
    confirmed_at = Column(DateTime)
    confirmed_by = Column(String(255))  # Name or ID of person who confirmed

    # Notes
    notes = Column(String(1000))

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    practice = relationship("Practice", back_populates="appointments")
    caregiver = relationship("User", back_populates="appointments")
    audio_recordings = relationship("AudioRecording", back_populates="appointment", cascade="all, delete-orphan")
    photos = relationship("Photo", back_populates="appointment", cascade="all, delete-orphan")
    transcription = relationship("NursingTranscription", back_populates="appointment", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Appointment(id={self.id}, uuid={self.uuid}, patient={self.patient_name})>"
