import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.booking import PaymentStatus, PaymentMethod


class PaymentInitiateRequest(BaseModel):
    booking_id: uuid.UUID = Field(...)
    method: PaymentMethod = Field(default=PaymentMethod.MYANMYANPAY)
    return_url: Optional[HttpUrl] = Field(None)
    cancel_url: Optional[HttpUrl] = Field(None)


class PaymentInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    booking_id: uuid.UUID
    transaction_id: str = Field(...)
    qr_code: str = Field(..., description="EMVCo QR Code String")

    payment_url: str = Field(...)
    expiry_date: datetime = Field(...)
    amount: Decimal
    currency: str = "MMK"
    status: PaymentStatus
    vendor: Optional[str] = None


# ==============================================
# Payment Callback / Webhook (MyanMyanPay -> Our System)
# ==============================================
class PaymentCallbackRequest(BaseModel):
    transaction_id: str = Field(...)
    order_id: Optional[str] = Field(None)
    status: str = Field(..., description="Payment status from gateway (SUCCESS, FAILED, PENDING)")
    amount: Decimal
    currency: Optional[str] = "MMK"
    payment_method: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = Field(None, description="MyanMyanPay return Full JSON Data")


class PaymentCallbackResponse(BaseModel):
    """Webhook ကို ကိုင်တွယ်ပြီးနောက် MyanMyanPay ဆီပြန်ပို့ရမည့် Response"""
    status: str = "SUCCESS"
    message: str = "Payment confirmed successfully"


# ==============================================
# Payment General Schemas
# ==============================================
class PaymentBase(BaseModel):
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="MMK", min_length=3, max_length=10)
    method: PaymentMethod


class PaymentCreate(PaymentBase):
    booking_id: uuid.UUID


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatus] = None
    transaction_id: Optional[str] = None
    gateway_data: Optional[Dict[str, Any]] = None
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    notes: Optional[str] = None

    vendor: Optional[str] = None
    gateway_method: Optional[str] = None



class PaymentResponse(PaymentBase):
    id: uuid.UUID
    booking_id: uuid.UUID
    status: PaymentStatus
    transaction_id: Optional[str] = None
    payment_url: Optional[str] = None
    gateway_data: Optional[Dict[str, Any]] = None
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentStatusResponse(BaseModel):
    """Booking တစ်ခုအတွက် Payment Status အကျဉ်းချုပ်"""
    booking_id: uuid.UUID
    total_paid: Decimal
    total_refunded: Decimal
    payment_status: PaymentStatus
    latest_payment_id: Optional[uuid.UUID] = None


