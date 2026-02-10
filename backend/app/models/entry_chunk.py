"""
EntryChunk model - stores individual semantic chunks from a transcription.

Each Entry can have multiple chunks, each independently categorized.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class EntryChunk(Base):
    __tablename__ = "entry_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("entries.id", ondelete="CASCADE"))
    
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, default="")
    
    # Per-chunk categorization
    category_id: Mapped[Optional[int]] = mapped_column(ForeignKey("category_definitions.id"), nullable=True)
    evidence_snippet: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Flag: has this chunk been stored in ChromaDB?
    embedding_stored: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    entry: Mapped["Entry"] = relationship(back_populates="chunks")
    category_definition: Mapped[Optional["CategoryDefinition"]] = relationship()
