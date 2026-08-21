from typing import Optional
from uuid import UUID
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class PromotionStatusEnum(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DISABLED = "disabled"


class UsageStatusEnum(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    CANCELLED = "cancelled"



class PromotionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None)
    promo_code: str = Field(..., min_length=1, max_length=50, pattern=r'^[A-Z0-9_]+$')
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    discount_amount: Optional[float] = Field(None, ge=0)
    max_usage: int = Field(1, ge=1)
    max_usage_per_user: int = Field(1, ge=1)
    expires_at: datetime = Field(...)
    is_active: bool = Field(True)

    @model_validator(mode="after")
    def validate_discount(self):
        if self.discount_percentage is None and self.discount_amount is None:
            raise ValueError("Either discount_percentage or discount_amount must be provided")
        return self


class PromotionCreate(PromotionBase):
    pass

class PromotionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    promo_code: Optional[str] = Field(None, min_length=1, max_length=50)
    discount_percentage: Optional[float] = Field(None, ge=0, le=100)
    discount_amount: Optional[float] = Field(None, ge=0)
    max_usage: Optional[int] = Field(None, ge=1)
    max_usage_per_user: Optional[int] = Field(None, ge=1)
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None
    status: Optional[PromotionStatusEnum] = None

class PromotionResponse(PromotionBase):
    id: UUID
    status: PromotionStatusEnum
    created_at: datetime
    updated_at: datetime
    current_usage_count: int = 0
    is_expired: bool = False
    is_fully_used: bool = False

    class Config:
        from_attributes = True


# ============================================
# Promotion Usage
# ============================================
class PromotionUsageBase(BaseModel):
    promotion_id: UUID = Field(...)
    booking_id: Optional[UUID] = None


class PromotionUsageCreate(PromotionUsageBase):
    user_id: UUID = Field(...)
    discount_amount_applied: float = Field(..., ge=0)


class PromotionUsageUpdate(BaseModel):
    status: Optional[UsageStatusEnum] = None
    booking_id: Optional[UUID] = None
    discount_amount_applied: Optional[float] = Field(None, ge=0)


class PromotionUsageResponse(PromotionUsageBase):
    id: UUID
    user_id: UUID
    status: UsageStatusEnum
    discount_amount_applied: float
    used_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    promotion: Optional[PromotionResponse] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class ApplyPromotionRequest(BaseModel):
    promo_code: str = Field(..., description="Promo code to apply")
    booking_total: float = Field(..., ge=0, description="Total booking amount before discount")


class ApplyPromotionResponse(BaseModel):
    promotion_id: UUID
    promo_code: str
    promotion_name: str
    discount_percentage: Optional[float] = None
    discount_amount: Optional[float] = None
    discount_applied: float
    final_total: float
    is_valid: bool = True
    message: Optional[str] = None


