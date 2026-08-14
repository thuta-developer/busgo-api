import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.seat import BusType, SeatPosition

class SeatCreate(BaseModel):
    seat_number: str
    row_number: int
    column_number: int
    position: SeatPosition

class BusSeatResponse(BaseModel):
    id: uuid.UUID
    bus_id: uuid.UUID
    seat_number: str
    row_number: int
    column_number: int
    position: SeatPosition
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class GenerateSeatsRequest(BaseModel):
    layout_type: BusType 
    total_seats: int