from typing import List, Optional
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.associations import role_permissions

class Permission(BaseModel):
    __tablename__ = "permissions"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="Unique key e.g., 'bus:create'"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    module: Mapped[Optional[str]] = mapped_column(
        String(50), index=True, nullable=True, comment="Group permissions by module e.g., 'Bus', 'Booking'"
    )

class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, index=True, nullable=False, comment="Role name e.g., 'Counter Staff'"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    permissions: Mapped[List[Permission]] = relationship(
        secondary=role_permissions,
        lazy="selectin"
    )