from typing import List
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.rbac import Role
from app.models.associations import user_roles


class User(BaseModel):
    __tablename__ = "users"

    email : Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    full_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    phone_number: Mapped[str | None] = mapped_column(
        String(20), index=True, nullable=True, unique=True
    )

    account_type: Mapped[str] = mapped_column(
        String(100), default='customer', nullable=False, comment="Account type: customer or staff"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_superuser : Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    last_login: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True),
    nullable=True,
    comment="Last successful login timestamp",
    )

    roles: Mapped[List[Role]] = relationship(
        secondary=user_roles,
        lazy="selectin"
    )

