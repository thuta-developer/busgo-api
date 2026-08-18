import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.models.trip_seat import TripSeatStatus


class TripSeatBase(BaseModel):
    trip_id: uuid.UUID
    seat_id: uuid.UUID
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

    # Optional nested data
    seat_number: Optional[str] = None
    row_number: Optional[int] = None
    column_number: Optional[int] = None
    position: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TripSeatBulkResponse(BaseModel):
    trip_id: uuid.UUID
    seats: list[TripSeatResponse]