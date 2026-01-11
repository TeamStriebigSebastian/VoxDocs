"""
Task model for storing extracted tasks from transcriptions.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class TaskPriority(str, enum.Enum):
    """Priority levels for tasks."""
    HIGH = "hoch"
    MEDIUM = "mittel"
    LOW = "niedrig"


class TaskStatus(str, enum.Enum):
    """Status of a task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Task(Base):
    """Model for tasks extracted from transcriptions."""

    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    transcription_id = Column(Integer, ForeignKey("transcriptions.id"), nullable=False)

    # Task details
    description = Column(Text, nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)

    # Scheduling
    due_date = Column(String(100))  # e.g., "nächster Termin", "in 2 Wochen"

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Patient/context info
    tooth_reference = Column(String(50), nullable=True)  # e.g., "Zahn 36"
    category = Column(String(50), nullable=True)  # e.g., "Kontrolle", "Behandlung"

    # Relationships
    transcription = relationship("Transcription", back_populates="tasks")

    def __repr__(self):
        return f"<Task {self.id}: {self.description[:30]}...>"
