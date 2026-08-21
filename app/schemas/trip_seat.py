import uuid
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from app.models.trip_seat import TripSeatStatus
from app.schemas.bus import BusResponse


class TripSeatBase(BaseModel):
    trip_id: uuid.UUID
    seat_id: uuid.UUID
    travel_date : date
    price: Optional[Decimal] = Decimal("0.00")
    status: TripSeatStatus = TripSeatStatus.AVAILABLE


class TripSeatCreate(TripSeatBase):
    pass


class TripSeatUpdate(BaseModel):
    status: Optional[TripSeatStatus] = None
    booked_by: Optional[uuid.UUID] = None
    booked_at: Optional[datetime] = None


class TripSeatResponse(TripSeatBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    booked_by: Optional[uuid.UUID] = None
    booked_at: Optional[datetime] = None
    hold_expires_at: Optional[datetime] = None

    


    # Optional nested data
    seat_number: Optional[str] = None
    row_number: Optional[int] = None
    column_number: Optional[int] = None
    position: Optional[str] = None

    # Bus data
    bus: Optional[BusResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TripSeatBulkResponse(BaseModel):
    trip_id: uuid.UUID
    seats: List[TripSeatResponse]


class BulkSeatRequest(BaseModel):
    travel_date : date
    seat_ids: List[uuid.UUID] = Field(
        ...,
        min_length=1,
        description="Seat ID များ (TripSeat.id သို့မဟုတ် Seat.id ဖြစ်နိုင်သည်)",
    )


class BulkHoldRequest(BulkSeatRequest):
    """Hold လုပ်လိုသော ခုံ ID များ"""
    pass


class BulkBookRequest(BulkSeatRequest):
    """Book လုပ်လိုသော ခုံ ID များ"""
    pass


class BulkConfirmRequest(BulkSeatRequest):
    """Confirm လုပ်လိုသော ခုံ ID များ"""
    pass


class BulkReleaseRequest(BulkSeatRequest):
    """Release လုပ်လိုသော ခုံ ID များ"""
    pass