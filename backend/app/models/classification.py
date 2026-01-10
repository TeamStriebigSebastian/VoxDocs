"""
Classification database models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class CategoryType(str, enum.Enum):
    """Types of classification categories."""
    FINDING = "finding"  # Befunde
    DIAGNOSIS = "diagnosis"  # Diagnosen
    TREATMENT = "treatment"  # Behandlungsschritte
    MATERIAL = "material"  # Materialverbrauch
    INSTRUMENT = "instrument"  # Instrumente
    ANATOMY = "anatomy"  # Anatomische Begriffe
    TOOTH = "tooth"  # Zahnbezeichnungen
    SURFACE = "surface"  # Flächenbeschreibungen
    OTHER = "other"


class ClassificationCategory(Base):
    """Model for classification categories."""

    __tablename__ = "classification_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(Enum(CategoryType), nullable=False)
    description = Column(Text)
    keywords = Column(Text)  # Comma-separated keywords

    # Relationships
    classifications = relationship("Classification", back_populates="category")

    def __repr__(self):
        return f"<ClassificationCategory(id={self.id}, name={self.name})>"


class Classification(Base):
    """Model for transcription classifications."""

    __tablename__ = "classifications"

    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("classification_categories.id"), nullable=False)

    # Extracted information
    extracted_text = Column(Text, nullable=False)
    normalized_value = Column(String(255))  # Normalized/standardized value

    # Position in original text
    start_position = Column(Integer)
    end_position = Column(Integer)

    # Dental-specific fields
    tooth_number = Column(String(10))  # FDI notation (e.g., "16", "47")
    surface = Column(String(50))  # mesial, distal, bukkal, etc.

    # Confidence
    confidence_score = Column(Float, nullable=False)
    model_version = Column(String(50))

    # Verification
    is_verified = Column(Integer, default=False)
    verified_by_user_id = Column(Integer, ForeignKey("users.id"))
    verified_at = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    transcription = relationship("Transcription", back_populates="classifications")
    category = relationship("ClassificationCategory", back_populates="classifications")

    def __repr__(self):
        return f"<Classification(id={self.id}, category_id={self.category_id}, confidence={self.confidence_score})>"
