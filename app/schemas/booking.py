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
    
    # Payment Data
    payment_method: PaymentMethod = PaymentMethod.MYANMYANPAY
    return_url: Optional[HttpUrl] = None
    cancel_url: Optional[HttpUrl] = None


class BookingWithPaymentResponse(BaseModel):
    """Booking နဲ့ Payment ကို တစ်ခါတည်း ပြန်ပို့ရန် Response"""
    booking: BookingResponse
    payment: PaymentInitiateResponse