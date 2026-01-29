from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

class CategoryDefinition(Base):
    __tablename__ = "category_definitions"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"))
    
    name: Mapped[str] = mapped_column(String(255))
    guidelines: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Markdown
    keywords: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Comma-separated keywords
    structure_schema: Mapped[dict] = mapped_column(JSON, default={}) # JSON Schema
    
    version: Mapped[int] = mapped_column(Integer, default=1)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    group: Mapped["Group"] = relationship(back_populates="category_definitions")
    entries: Mapped[List["Entry"]] = relationship(back_populates="category_definition")
