"""
Transcription database models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class Transcription(Base):
    """Model for transcription results."""

    __tablename__ = "transcriptions"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("audio_recordings.id"), unique=True, nullable=False)

    # Transcription content
    full_text = Column(Text, nullable=False)
    language = Column(String(10), default="de")

    # Processing metadata
    whisper_model = Column(String(50))
    processing_time_seconds = Column(Float)
    confidence_score = Column(Float)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Correction tracking
    correction_count = Column(Integer, default=0)
    last_corrected_at = Column(DateTime)

    # Relationships
    recording = relationship("AudioRecording", back_populates="transcription")
    segments = relationship("TranscriptionSegment", back_populates="transcription", cascade="all, delete-orphan")
    classifications = relationship("Classification", back_populates="transcription", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Transcription(id={self.id}, recording_id={self.recording_id})>"


class TranscriptionSegment(Base):
    """Model for transcription segments with timestamps."""

    __tablename__ = "transcription_segments"

    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False)

    # Segment content
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)

    # Confidence and metadata
    confidence = Column(Float)
    speaker_id = Column(String(50))  # For future speaker diarization

    # Word-level timestamps (JSON array)
    word_timestamps = Column(JSON)

    # Relationships
    transcription = relationship("Transcription", back_populates="segments")

    def __repr__(self):
        return f"<TranscriptionSegment(id={self.id}, start={self.start_time}, end={self.end_time})>"
