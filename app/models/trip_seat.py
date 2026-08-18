import uuid
import enum
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, ForeignKey, Boolean, DateTime, UniqueConstraint, CheckConstraint, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.trip import Trip
    from app.models.seat import Seat
    from app.models.user import User


class TripSeatStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    HELD = "HELD"
    BOOKED = "BOOKED"
    CANCELLED = "CANCELLED"


class TripSeat(BaseModel):
    __tablename__ = "trip_seats"
    __table_args__ = (
        UniqueConstraint("trip_id", "seat_id", name="uq_trip_seat"),
        CheckConstraint(
            "status IN ('AVAILABLE', 'HELD', 'BOOKED', 'CANCELLED')",
            name="ck_trip_seat_status"
        ),
    )

    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False
    )
    seat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seats.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[TripSeatStatus] = mapped_column(
        SQLEnum(TripSeatStatus, name="trip_seat_status"),
        default=TripSeatStatus.AVAILABLE,
        nullable=False,
        index=True,

    )

    hold_expires_at : Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    booked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    booked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    trip: Mapped["Trip"] = relationship("Trip", back_populates="trip_seats")
    seat: Mapped["Seat"] = relationship("Seat", back_populates="trip_seats")
    user: Mapped["User"] = relationship("User", back_populates="trip_seats") 
