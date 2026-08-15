import uuid
from datetime import datetime, time, date
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator
from app.models.trip import TripStatus


class TripBase(BaseModel):
    bus_id: uuid.UUID
    route_id: uuid.UUID
    departure_time: time  
    arrival_time: time 

    local_price: Decimal = Field(
        gt=0, description="Local price in MMK, must be positive"
    )
    foreigner_price: Decimal = Field(
        gt=0, description="Foreigner price in MMK, must be positive"
    )
    local_festival_price: Optional[Decimal] = Field(None, gt=0)
    foreigner_festival_price: Optional[Decimal] = Field(None, gt=0)

    booking_open_date: datetime
    booking_close_date: datetime
    festival_start_date: Optional[datetime] = None
    festival_end_date: Optional[datetime] = None

    status: TripStatus = TripStatus.SCHEDULED
    is_active: bool = True

    @model_validator(mode="after")
    def validate_dates(self) -> "TripBase":
        if self.arrival_time <= self.departure_time:
            raise ValueError("arrival_time must be after departure_time")

        if self.booking_close_date <= self.booking_open_date:
            raise ValueError("booking_close_date must be after booking_open_date")

        if self.festival_start_date and self.festival_end_date:
            if self.festival_end_date <= self.festival_start_date:
                raise ValueError("festival_end_date must be after festival_start_date")

        # Festival dates must be within booking window
        if (
            self.festival_start_date
            and self.festival_start_date < self.booking_open_date
        ):
            raise ValueError("festival_start_date must be within the booking window")

        if self.festival_end_date and self.festival_end_date > self.booking_close_date:
            raise ValueError("festival_end_date must be within the booking window")

        return self


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    bus_id: Optional[uuid.UUID] = None
    route_id: Optional[uuid.UUID] = None
    departure_time: Optional[time] = None
    arrival_time: Optional[time] = None  
    local_price: Optional[Decimal] = Field(None, gt=0)
    foreigner_price: Optional[Decimal] = Field(None, gt=0)
    local_festival_price: Optional[Decimal] = Field(None, gt=0)
    foreigner_festival_price: Optional[Decimal] = Field(None, gt=0)
    booking_open_date: Optional[datetime] = None
    booking_close_date: Optional[datetime] = None
    festival_start_date: Optional[datetime] = None
    festival_end_date: Optional[datetime] = None
    status: Optional[TripStatus] = None
    is_active: Optional[bool] = None

    @model_validator(mode="after")
    def validate_dates(self) -> "TripUpdate":
        if self.departure_time and self.arrival_time:
            if self.arrival_time <= self.departure_time:
                raise ValueError("arrival_time must be after departure_time")

        if self.booking_open_date and self.booking_close_date:
            if self.booking_close_date <= self.booking_open_date:
                raise ValueError("booking_close_date must be after booking_open_date")

        if self.festival_start_date and self.festival_end_date:
            if self.festival_end_date <= self.festival_start_date:
                raise ValueError("festival_end_date must be after festival_start_date")

        return self


class TripPriceResponse(BaseModel):
    trip_id: uuid.UUID
    base_price: Decimal
    final_price: Decimal
    price_type: str  # local / foreigner / festival local / festival foreigner
    is_festival: bool
    user_type: str  # local / foreigner
    currency: str = "MMK"


class TripResponse(TripBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    route_origin: Optional[str] = None
    route_destination: Optional[str] = None
    bus_number: Optional[str] = None
    company_name: Optional[str] = None
    company_logo_url: Optional[str] = None
    bus_type: Optional[str] = None

    # Current trip price payload for the default user type
    price: Optional[TripPriceResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TripFilter(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    travel_date: Optional[date] = None
    user_type: str = "local"
    time_of_day: Optional[str] = None
    bus_type: Optional[str] = None
    include_bookable_only: bool = True