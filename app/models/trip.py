import uuid
import enum
from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, List
from sqlalchemy import (
    String,
    Float,
    ForeignKey,
    Enum as SQLEnum,
    Boolean,
    DateTime,
    Numeric,
    CheckConstraint,
    Time as SQLTime, 
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.route import Route
    from app.models.bus import Bus
    from app.models.trip_seat import TripSeat
    from app.models.booking import Booking


class TripStatus(str, enum.Enum):
    SCHEDULED = "SCHEDULED"
    IN_TRANSIT = "IN_TRANSIT"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Trip(BaseModel):
    __tablename__ = "trips"
    __table_args__ = (
        CheckConstraint(
            "arrival_time > departure_time",
            name="ck_trips_arrival_after_departure",
        ),
        CheckConstraint(
            "booking_close_date > booking_open_date",
            name="ck_trips_booking_close_after_open",
        ),
        CheckConstraint(
            "local_price >= 0",
            name="ck_trips_local_price_non_negative",
        ),
        CheckConstraint(
            "foreigner_price >= 0",
            name="ck_trips_foreigner_price_non_negative",
        ),
    )

    bus_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buses.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="CASCADE"), nullable=False
    )

    departure_time: Mapped[time] = mapped_column(
        SQLTime, nullable=False, index=True
    )
    arrival_time: Mapped[time] = mapped_column(
        SQLTime, nullable=False
    )

    local_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    foreigner_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    local_festival_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    foreigner_festival_price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )

    booking_open_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    booking_close_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    festival_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    festival_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    status: Mapped[TripStatus] = mapped_column(
        SQLEnum(TripStatus, name="trip_status"),
        default=TripStatus.SCHEDULED,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    route: Mapped["Route"] = relationship("Route", back_populates="trips")
    bus: Mapped["Bus"] = relationship("Bus", back_populates="trips")
    trip_seats: Mapped[List["TripSeat"]] = relationship("TripSeat", back_populates="trip", cascade="all, delete-orphan")
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="trip")
