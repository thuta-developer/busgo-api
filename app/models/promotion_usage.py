import enum
import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import Float, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.promotion import Promotion
    from app.models.user import User
    from app.models.booking import Booking


class UsageStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    CANCELLED = "cancelled"


class PromotionUsage(BaseModel):
    __tablename__ = "promotion_usages"

    status: Mapped[UsageStatus] = mapped_column(
        Enum(UsageStatus), nullable=False, default=UsageStatus.PENDING
    )
    discount_amount_applied: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )

    # Foreign Keys
    promotion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promotions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Promotion ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who used this promotion",
    )
    booking_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Booking ID (if applicable)",
    )

    # Relationships
    promotion: Mapped["Promotion"] = relationship("Promotion", back_populates="usages")
    user: Mapped["User"] = relationship("User", lazy="selectin")
    booking: Mapped[Optional["Booking"]] = relationship("Booking", back_populates="promotion_usage")

    def __repr__(self) -> str:
        return f"<PromotionUsage {self.promotion_id} by {self.user_id} ({self.status.value})>"