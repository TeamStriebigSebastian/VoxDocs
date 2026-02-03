from sqlalchemy import Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import enum
from sqlalchemy import Enum as SQLEnum

class UserRole(str, enum.Enum):
    ADMIN = "admin" # Platform Admin
    SUPERUSER = "superuser" # Group Admin
    USER = "user" # Standard User
    VIEWER = "viewer" # Read-Only Viewer

class UserGroupRole(Base):
    __tablename__ = "user_group_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), primary_key=True)
    
    role: Mapped[UserRole] = mapped_column(SQLEnum(UserRole), default=UserRole.USER)
    can_manage_users: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="group_roles")
    group: Mapped["Group"] = relationship(back_populates="user_roles")
