import enum
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.promotion_usage import PromotionUsage


class PromotionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class Promotion(BaseModel):
    __tablename__ = "promotions"

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True, comment="Promotion name"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Promotion description"
    )
    promo_code: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True, comment="Promotion code"
    )
    discount_percentage: Mapped[float] = mapped_column(
        Float, nullable=False, comment="Discount percentage for the promotion"
    )
    discount_amount: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Discount amount for the promotion"
    )

    max_usage: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Maximum number of times the promotion can be used"
    )
    max_usage_per_user: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, comment="Maximum times a single user can use this promotion"
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="Promotion expiration date"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Indicates if the promo is active"
    )

    status: Mapped[PromotionStatus] = mapped_column(
        Enum(PromotionStatus), nullable=False, default=PromotionStatus.ACTIVE
    )

    # Relationships
    usages: Mapped[list["PromotionUsage"]] = relationship(
        "PromotionUsage",
        back_populates="promotion",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def current_usage_count(self) -> int:
        return len(self.usages) if self.usages else 0

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_fully_used(self) -> bool:
        return self.current_usage_count >= self.max_usage