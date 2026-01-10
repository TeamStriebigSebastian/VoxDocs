"""
Onboarding and phrase recording database models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class OnboardingStatus(str, enum.Enum):
    """Status of onboarding session."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PhraseCategory(str, enum.Enum):
    """Categories of dental phrases for onboarding."""
    TOOTH_DESIGNATION = "tooth_designation"  # Zahnbezeichnungen
    SURFACE = "surface"  # Flächenbeschreibungen
    DIAGNOSIS = "diagnosis"  # Diagnosen
    FINDING = "finding"  # Befunde
    TREATMENT = "treatment"  # Behandlungsschritte
    MATERIAL = "material"  # Materialien
    INSTRUMENT = "instrument"  # Instrumente
    ANATOMY = "anatomy"  # Anatomische Begriffe
    SENTENCE = "sentence"  # Realistische Satzkombinationen


class OnboardingSession(Base):
    """Model for onboarding sessions."""

    __tablename__ = "onboarding_sessions"

    id = Column(Integer, primary_key=True, index=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Speaker information for training data
    speaker_name = Column(String(255))  # Name/identifier of the person recording
    speaker_notes = Column(Text)  # Optional notes about the speaker

    # Session status
    status = Column(Enum(OnboardingStatus), default=OnboardingStatus.NOT_STARTED)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)

    # Progress tracking
    total_phrases = Column(Integer, default=250)
    completed_phrases = Column(Integer, default=0)
    current_category = Column(Enum(PhraseCategory))

    # Session metadata
    estimated_duration_minutes = Column(Integer, default=15)
    actual_duration_minutes = Column(Float)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    practice = relationship("Practice", back_populates="onboarding_sessions")
    user = relationship("User", back_populates="onboarding_sessions")
    phrase_recordings = relationship("PhraseRecording", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<OnboardingSession(id={self.id}, user_id={self.user_id}, status={self.status})>"


class PhraseRecording(Base):
    """Model for individual phrase recordings during onboarding."""

    __tablename__ = "phrase_recordings"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("onboarding_sessions.id"), nullable=False)

    # Phrase information
    phrase_text = Column(Text, nullable=False)
    category = Column(Enum(PhraseCategory), nullable=False)
    phrase_index = Column(Integer)  # Order in the category

    # Recording information
    encrypted_filename = Column(String(255))
    duration_seconds = Column(Float)

    # Validation
    is_valid = Column(Boolean, default=True)
    validation_score = Column(Float)  # Audio quality score
    needs_rerecording = Column(Boolean, default=False)

    # Timestamps
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("OnboardingSession", back_populates="phrase_recordings")

    def __repr__(self):
        return f"<PhraseRecording(id={self.id}, phrase={self.phrase_text[:30]}...)>"
