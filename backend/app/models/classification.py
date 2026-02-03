"""
Classification database models.
Simplified for LLM-generated classifications.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class Classification(Base):
    """Model for LLM-generated transcription classifications."""

    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False)

    # LLM classification output
    category = Column(String(50), nullable=False)  # befund, behandlung, planung, anamnese, aufgabe
    text = Column(Text, nullable=False)  # The classified text segment
    confidence = Column(Float, default=0.8)

    # Verification for training feedback
    is_verified = Column(Boolean, default=False)
    verified_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transcription = relationship("Transcription", back_populates="classifications")

    def __repr__(self):
        return f"<Classification(id={self.id}, category={self.category})>"
