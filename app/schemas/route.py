from typing import Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class RouteBase(BaseModel):
    origin: str
    destination: str
    distance_km: Optional[float] = Field(None, gt=0, description="Distance in kilometers, must be positive")
    estimated_hours: Optional[float] = Field(None, gt=0, description="Estimated travel time in hours, must be positive")
    is_active: bool = True

    @field_validator("origin", "destination")
    @classmethod
    def normalize_location(cls, v: str) -> str:
        """Strip whitespace and normalize to Title Case for consistent data."""
        if not v or not v.strip():
            raise ValueError("Location cannot be empty")
        return v.strip().title()

    @model_validator(mode="after")
    def validate_origin_not_destination(self):
        """Ensure origin and destination are not the same (case-insensitive)."""
        if self.origin.lower() == self.destination.lower():
            raise ValueError("Origin and destination cannot be the same")
        return self


class RouteCreate(RouteBase):
    pass


class RouteUpdate(BaseModel):
    origin: Optional[str] = None
    destination: Optional[str] = None
    distance_km: Optional[float] = Field(None, gt=0, description="Distance in kilometers, must be positive")
    estimated_hours: Optional[float] = Field(None, gt=0, description="Estimated travel time in hours, must be positive")
    is_active: Optional[bool] = None

    @field_validator("origin", "destination")
    @classmethod
    def normalize_location(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and normalize to Title Case for consistent data."""
        if v is None:
            return v
        if not v.strip():
            raise ValueError("Location cannot be empty")
        return v.strip().title()

    @model_validator(mode="after")
    def validate_origin_not_destination(self):
        """Ensure origin and destination are not the same (case-insensitive)."""
        if self.origin and self.destination and self.origin.lower() == self.destination.lower():
            raise ValueError("Origin and destination cannot be the same")
        return self


class RouteResponse(RouteBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)