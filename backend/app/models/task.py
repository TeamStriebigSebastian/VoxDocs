from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base

class TaskType(str, enum.Enum):
    ONE_SHOT = "one_shot"
    REMINDER_ONCE = "reminder_once"
    RECURRING_ALWAYS = "recurring_always"
    RECURRING_INTERVAL = "recurring_interval"

class TaskStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), default=lambda: str(uuid.uuid4()))
    case_id: Mapped[int] = mapped_column(ForeignKey("case_files.id"))
    
    title: Mapped[str] = mapped_column(String(255))
    task_type: Mapped[TaskType] = mapped_column(SQLEnum(TaskType))
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.ACTIVE)
    
    repeat_interval_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # Simple interval
    next_due_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case_file: Mapped["CaseFile"] = relationship(back_populates="tasks")
    translations: Mapped[list["TaskTranslation"]] = relationship(back_populates="task", cascade="all, delete-orphan")
