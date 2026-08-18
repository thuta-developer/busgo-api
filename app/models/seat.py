import enum
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import List

from app.models.bus import Bus
from app.models.base import BaseModel
from app.models.trip_seat import TripSeat

class BusType(str, enum.Enum):
    VIP_2_1 = "2:1"  # VIP 3 Columns (2 + 1)
    STANDARD_2_2 = "2:2"  # Standard 4 Columns (2 + 2)


class SeatPosition(str, enum.Enum):
    LEFT_WINDOW = "LEFT_WINDOW"
    LEFT_AISLE = "LEFT_AISLE"
    RIGHT_AISLE = "RIGHT_AISLE"
    RIGHT_WINDOW = "RIGHT_WINDOW"


class Seat(BaseModel):
    __tablename__ = "seats"

    bus_id : Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("buses.id", ondelete="CASCADE"), nullable=False
    )

    seat_number : Mapped[str] = mapped_column(String(20), nullable=False)
    row_number : Mapped[int] = mapped_column(Integer, nullable=False)
    column_number : Mapped[int] = mapped_column(Integer, nullable=False)
    position : Mapped[SeatPosition] = mapped_column(SQLEnum(SeatPosition), nullable=False)
    is_active : Mapped[bool] = mapped_column(Boolean, default=True)

    bus : Mapped["Bus"] = relationship("Bus", back_populates="seats")
    trip_seats: Mapped[List["TripSeat"]] = relationship("TripSeat", back_populates="seat", cascade="all, delete-orphan")