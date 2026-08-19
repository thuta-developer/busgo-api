import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import (
    String, ForeignKey, Enum as SQLEnum, DateTime, 
    Numeric, CheckConstraint, Index, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB 
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.models.booking import PaymentStatus, PaymentMethod

if TYPE_CHECKING:
    from app.models.booking import Booking


class Payment(BaseModel):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payment_amount_non_negative"),
        Index("idx_payment_booking_id", "booking_id"),
        Index("idx_payment_status", "status"),
        Index("idx_payment_transaction_id", "transaction_id", unique=True),
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False
    )

    # ===== Payment Information =====
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="MMK")
    method: Mapped[PaymentMethod] = mapped_column(
        SQLEnum(PaymentMethod, name="payment_method"), nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus, name="payment_status"),
        default=PaymentStatus.PENDING,
        nullable=False,
        index=True,
    )

    # ===== Payment Gateway Fields (MyanMyanPay) =====
    transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    payment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    vendor: Mapped[str | None] = mapped_column(
        String(50), nullable=True, index=True
    )  # KBZPay, WavePay, CBPay

    gateway_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )

    gateway_method: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ===== Timestamps =====
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expiry_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ===== Notes =====
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== Relationships =====
    booking: Mapped["Booking"] = relationship("Booking", back_populates="payments")