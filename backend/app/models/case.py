from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import enum
import uuid

from app.core.database import Base

class CaseStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    LOCKED = "locked"

class CaseFile(Base):
    __tablename__ = "case_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    
    title: Mapped[str] = mapped_column(String(255))
    external_ref: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[CaseStatus] = mapped_column(SQLEnum(CaseStatus), default=CaseStatus.ACTIVE)
    
    owner_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True) # Primary owner/creator
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    group: Mapped["Group"] = relationship(back_populates="case_files")
    entries: Mapped[List["Entry"]] = relationship(back_populates="case_file", order_by="Entry.created_at")
    tasks: Mapped[List["Task"]] = relationship(back_populates="case_file")
    # access_grants: Mapped[List["CaseAccess"]] = relationship(back_populates="case_file")
