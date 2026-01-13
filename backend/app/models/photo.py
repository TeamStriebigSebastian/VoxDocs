"""
Photo model for nursing care documentation.
Photos are attached to appointments.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class Photo(Base):
    """Model for photos taken during nursing care appointments."""

    __tablename__ = "photos"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), unique=True, index=True, nullable=False)

    # Appointment reference
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False)

    # File information
    original_filename = Column(String(255))
    encrypted_filename = Column(String(255), nullable=False)
    file_size_bytes = Column(Integer)
    mime_type = Column(String(50), default="image/jpeg")

    # Metadata
    caption = Column(String(500))  # Optional description
    taken_at = Column(DateTime, default=datetime.utcnow)

    # Storage
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    appointment = relationship("Appointment", back_populates="photos")

    def __repr__(self):
        return f"<Photo(id={self.id}, uuid={self.uuid}, appointment_id={self.appointment_id})>"
