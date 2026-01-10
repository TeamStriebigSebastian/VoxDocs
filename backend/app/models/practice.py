"""
Practice, Room, and User database models.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles in the system."""
    ADMIN = "admin"
    DENTIST = "dentist"
    ASSISTANT = "assistant"
    TECHNICIAN = "technician"


class Practice(Base):
    """Model for dental practices."""

    __tablename__ = "practices"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    phone = Column(String(50))
    email = Column(String(255))

    # Settings
    default_language = Column(String(10), default="de")
    retention_days = Column(Integer, default=90)

    # Encryption
    encryption_key_hash = Column(String(255))  # Hash of practice-specific key

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    rooms = relationship("Room", back_populates="practice", cascade="all, delete-orphan")
    users = relationship("User", back_populates="practice", cascade="all, delete-orphan")
    recordings = relationship("AudioRecording", back_populates="practice")
    onboarding_sessions = relationship("OnboardingSession", back_populates="practice")

    def __repr__(self):
        return f"<Practice(id={self.id}, name={self.name})>"


class Room(Base):
    """Model for treatment rooms."""

    __tablename__ = "rooms"

    id = Column(Integer, primary_key=True, index=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)
    name = Column(String(100), nullable=False)
    room_number = Column(String(20))
    description = Column(String(500))

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    practice = relationship("Practice", back_populates="rooms")
    recordings = relationship("AudioRecording", back_populates="room")

    def __repr__(self):
        return f"<Room(id={self.id}, name={self.name})>"


class User(Base):
    """Model for system users (dentists, assistants)."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    practice_id = Column(Integer, ForeignKey("practices.id"), nullable=False)

    # User information
    email = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.ASSISTANT)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime)

    # Relationships
    practice = relationship("Practice", back_populates="users")
    recordings = relationship("AudioRecording", back_populates="recorded_by")
    onboarding_sessions = relationship("OnboardingSession", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
