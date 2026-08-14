import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Enum as SQLEnum, Boolean, UniqueConstraint, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel


class Route(BaseModel):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint("origin", "destination", name="uq_routes_origin_destination"),
        CheckConstraint(
            "lower(origin) <> lower(destination)",
            name="ck_routes_origin_not_destination",
        ),
    )

    origin: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    destination: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )
    distance_km: Mapped[float] = mapped_column(
        Float, nullable=True
    )
    estimated_hours: Mapped[float] = mapped_column(
        Float, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)