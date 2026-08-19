import uuid
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import ForeignKey, Numeric, CheckConstraint, String, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.booking import Booking
    from app.models.trip_seat import TripSeat


class BookingSeat(BaseModel):
    __tablename__ = "booking_seats"
    __table_args__ = (
        CheckConstraint("price_at_booking >= 0", name="ck_booking_seat_price_non_negative"),
        CheckConstraint("quantity = 1", name="ck_booking_seat_quantity_one"),
        CheckConstraint("row_number > 0", name="ck_booking_seat_row_positive"),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )
    trip_seat_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trip_seats.id", ondelete="RESTRICT"), nullable=False
    )

    # ===== Denormalized Seat Info (for historical accuracy) =====
    seat_number: Mapped[str] = mapped_column(String(20), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    column_number: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[str] = mapped_column(String(50), nullable=False)  # LEFT_WINDOW, etc.

    # ===== Pricing =====
    price_at_booking: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(default=1, nullable=False)

    # ===== Relationships =====
    booking: Mapped["Booking"] = relationship("Booking", back_populates="booking_seats")
    trip_seat: Mapped["TripSeat"] = relationship("TripSeat", back_populates="booking_seats")