from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid
import enum

from app.core.database import Base

class AudioStatus(str, enum.Enum):
    PENDING = "pending"
    TRANSCRIBED = "transcribed"
    FAILED = "failed"
    DELETED = "deleted" # Privacy compliant

class Entry(Base):
    __tablename__ = "entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    
    case_id: Mapped[int] = mapped_column(ForeignKey("case_files.id"))
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("category_definitions.id"), nullable=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    text: Mapped[str] = mapped_column(String, default="")
    structured_data: Mapped[dict] = mapped_column(JSON, default={})
    
    # Audio handling
    audio_object_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    audio_status: Mapped[Optional[AudioStatus]] = mapped_column(SQLEnum(AudioStatus), nullable=True)
    
    # Image handling
    image_object_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    # Versioning / Addenda configuration
    parent_entry_id: Mapped[Optional[int]] = mapped_column(ForeignKey("entries.id"), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    case_file: Mapped["CaseFile"] = relationship(back_populates="entries")
    category_definition: Mapped[Optional["CategoryDefinition"]] = relationship(back_populates="entries")
    author: Mapped["User"] = relationship(back_populates="entries")
    translations: Mapped[List["EntryTranslation"]] = relationship(back_populates="entry", cascade="all, delete-orphan")
    chunks: Mapped[List["EntryChunk"]] = relationship(back_populates="entry", cascade="all, delete-orphan", order_by="EntryChunk.chunk_index")
    
    # Adjacency list for history
    # Adjacency list for history
    parent: Mapped[Optional["Entry"]] = relationship("Entry", remote_side=[id], back_populates="children")
    children: Mapped[List["Entry"]] = relationship("Entry", back_populates="parent")
