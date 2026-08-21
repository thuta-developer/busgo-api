import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, EmailStr, field_validator, HttpUrl

from app.models.booking import BookingStatus
from app.schemas.payment import PaymentInitiateResponse, PaymentMethod


class BookingSeatBase(BaseModel):
    trip_seat_id: uuid.UUID
    price_at_booking: Decimal = Field(gt=0)

class BookingSeatCreate(BookingSeatBase):
    pass

class BookingSeatResponse(BookingSeatBase):
    id: uuid.UUID
    booking_id: uuid.UUID

    seat_number: str
    row_number: int
    column_number: int

    position: str
    
    model_config = ConfigDict(from_attributes=True)

class BookingBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr = Field(...)
    phone: str = Field(..., min_length=7, max_length=20)
    gender: str = Field(..., min_length=1, max_length=10)
    special_request: Optional[str] = Field(None, max_length=5000)

class BookingCreate(BookingBase):
    trip_id: uuid.UUID = Field(...)
    seat_ids: List[uuid.UUID] = Field(..., min_length=1)

    @field_validator("seat_ids")
    @classmethod
    def validate_seat_ids(cls, v: List[uuid.UUID]) -> List[uuid.UUID]:
        if len(v) != len(set(v)):
            raise ValueError("seat_ids must not contain duplicate ids.")
        return v

class BookingUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=7, max_length=20)
    gender: Optional[str] = Field(None)
    special_request: Optional[str] = Field(None, max_length=5000)

    status: Optional[BookingStatus] = None  

class BookingResponse(BookingBase):
    id : uuid.UUID
    booking_code: str
    status: BookingStatus
    total_seats: int

    # Pricing
    total_amount: Decimal
    service_fee: Decimal
    discount_amount: Decimal
    net_amount: Decimal

    # Timestamps
    travel_date: datetime
    expiry_date: datetime
    created_at: datetime
    updated_at: datetime
    
    # Relationships (Nested)
    trip_id: uuid.UUID
    user_id: uuid.UUID
    booking_seats: List[BookingSeatResponse] = []
    payment_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)




class BookingWithPaymentRequest(BaseModel):
    # Booking Data
    trip_id: uuid.UUID
    seat_ids: List[uuid.UUID] = Field(..., min_length=1)
    travel_date: date 
    user_type: Optional[str] = "local"
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=7, max_length=20)
    gender: str = Field(..., min_length=1, max_length=10)
    special_request: Optional[str] = None
    
    # Promotion Data (Optional)
    promo_code: Optional[str] = Field(None, description="Promo code to apply discount")
    
    # Payment Data
    payment_method: PaymentMethod = PaymentMethod.MYANMYANPAY
    return_url: Optional[HttpUrl] = None
    cancel_url: Optional[HttpUrl] = None


class BookingWithPaymentResponse(BaseModel):
    """Booking နဲ့ Payment ကို တစ်ခါတည်း ပြန်ပို့ရန် Response"""
    booking: BookingResponse
    payment: PaymentInitiateResponse


# ============================================
# Booking Price Preview (Summary)
# ============================================


class PricePreviewSeatItem(BaseModel):
    """Price Preview အတွက် ထိုင်ခုံ တစ်ခုချင်းစီ၏ အချက်အလက်"""
    trip_seat_id: uuid.UUID
    seat_id: Optional[uuid.UUID] = None
    seat_number: Optional[str] = None
    row_number: Optional[int] = None
    column_number: Optional[int] = None
    position: Optional[str] = None
    price: Decimal = Field(..., description="Computed price for this seat (festival/user_type aware)")


class BookingPricePreviewRequest(BaseModel):
    """Booking Form မှ Summary ကြည့်ရန် Price Preview ၏ Request"""
    trip_id: uuid.UUID = Field(...)
    seat_ids: List[uuid.UUID] = Field(..., min_length=1, description="TripSeat IDs (or Seat IDs)")
    travel_date: date = Field(...)
    user_type: Optional[str] = Field("local", description="local or foreigner")
    promo_code: Optional[str] = Field(None, description="Optional promo code to preview discount")

    @field_validator("seat_ids")
    @classmethod
    def validate_seat_ids(cls, v: List[uuid.UUID]) -> List[uuid.UUID]:
        if len(v) != len(set(v)):
            raise ValueError("seat_ids must not contain duplicate ids.")
        return v

    @field_validator("user_type")
    @classmethod
    def validate_user_type(cls, v: Optional[str]) -> str:
        normalized = (v or "local").lower()
        if normalized not in {"local", "foreigner"}:
            raise ValueError("user_type must be either 'local' or 'foreigner'")
        return normalized


class BookingPricePreviewResponse(BaseModel):
    """Booking Summary / Price Preview အတွက် Response"""
    trip_id: uuid.UUID
    travel_date: date
    user_type: str

    # Seat breakdown
    seats: List[PricePreviewSeatItem]
    total_seats: int = Field(..., description="Number of selected seats")

    # Price summary
    subtotal: Decimal = Field(..., description="Total seat prices before discount")
    service_fee: Decimal = Field(..., description="Service fee")
    total_amount: Decimal = Field(..., description="Subtotal + service fee (before discount)")

    # Promotion (if applied)
    promo_code: Optional[str] = None
    promotion_id: Optional[uuid.UUID] = None
    promotion_name: Optional[str] = None
    discount_percentage: Optional[float] = None
    discount_amount: Optional[float] = None
    discount_applied: Decimal = Field(Decimal("0.00"), description="Actual discount deducted")

    # Final amount to pay
    net_amount: Decimal = Field(..., description="Final amount after discount (what user pays)")

    is_valid: bool = True
    message: Optional[str] = None