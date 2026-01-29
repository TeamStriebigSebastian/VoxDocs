from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Boolean, JSON, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base

class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(36), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255))
    default_language: Mapped[str] = mapped_column(String(10), default="de")
    settings: Mapped[dict] = mapped_column(JSON, default={})
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    groups: Mapped[List["Group"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")
    users: Mapped[List["User"]] = relationship(back_populates="tenant", cascade="all, delete-orphan")


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="groups")
    case_files: Mapped[List["CaseFile"]] = relationship(back_populates="group")
    user_roles: Mapped[List["UserGroupRole"]] = relationship(back_populates="group")
    category_definitions: Mapped[List["CategoryDefinition"]] = relationship(back_populates="group")
