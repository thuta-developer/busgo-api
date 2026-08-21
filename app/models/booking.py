import uuid
import enum
from datetime import datetime, date
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import (
    String,
    ForeignKey,
    Enum as SQLEnum,
    DateTime,
    Numeric,
    Text,
    CheckConstraint,
    Index,
    Integer,
    Date,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.trip import Trip
    from app.models.trip_seat import TripSeat
    from app.models.payment import Payment
    from app.models.booking_seat import BookingSeat
    from app.models.promotion_usage import PromotionUsage


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    PAYMENT_EXPIRED = "PAYMENT_EXPIRED"
    REFUNDED = "REFUNDED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAID = "PAID"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    EXPIRED = "EXPIRED"


class PaymentMethod(str, enum.Enum):
    MYANMYANPAY = "MYANMYANPAY"
    # CASH = "CASH"
    # BANK_TRANSFER = "BANK_TRANSFER"


class Booking(BaseModel):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "total_amount >= 0", name="ck_booking_total_amount_non_negative"
        ),
        CheckConstraint("service_fee >= 0", name="ck_booking_service_fee_non_negative"),
        CheckConstraint(
            "discount_amount >= 0", name="ck_booking_discount_non_negative"
        ),
        Index("idx_booking_user_id", "user_id"),
        Index("idx_booking_trip_id", "trip_id"),
        Index("idx_booking_status", "status"),
        Index("idx_booking_booking_code", "booking_code", unique=True),
    )
    # ===== Relationships =====
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    trip_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("trips.id", ondelete="RESTRICT"), nullable=False
    )
    promotion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promotions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ===== Booking Information =====
    booking_code: Mapped[str] = mapped_column(
        String(20), nullable=False, unique=True, index=True
    )
    status: Mapped[BookingStatus] = mapped_column(
        SQLEnum(BookingStatus, name="booking_status"),
        default=BookingStatus.PENDING,
        nullable=False,
        index=True,
    )
    total_seats: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # User Info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    gender: Mapped[str] = mapped_column(String(10), nullable=False)
    special_request: Mapped[str | None] = mapped_column(Text, nullable=True)

    travel_date: Mapped[date] = mapped_column(Date, nullable=False)

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    service_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=0
    )  # total_amount + service_fee - discount_amount

    booking_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.now
    )
    expiry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )  # ငွေပေးချေရန် သတ်မှတ်ရက် (ဥပမာ - ၁၅ မိနစ်)

    # ===== Relationships =====
    user: Mapped["User"] = relationship("User", back_populates="bookings")
    trip: Mapped["Trip"] = relationship("Trip", back_populates="bookings")
    booking_seats: Mapped[List["BookingSeat"]] = relationship(
        "BookingSeat", back_populates="booking", cascade="all, delete-orphan"
    )
    payments: Mapped[List["Payment"]] = relationship(
        "Payment", back_populates="booking", cascade="all, delete-orphan"
    )
    promotion_usage: Mapped[Optional["PromotionUsage"]] = relationship(
        "PromotionUsage",
        back_populates="booking",
        uselist=False,
    )
