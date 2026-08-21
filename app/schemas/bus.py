import uuid
from typing import Optional, Union, Any
from pydantic import BaseModel, ConfigDict
from app.schemas.bus_company import BusCompanyResponse  # Import Company Schema
from datetime import datetime

class BusBase(BaseModel):
    company_id: uuid.UUID  # Company ID မဖြစ်မနေ ပါရမည်
    name: str
    bus_image_url : Optional[str]
    bus_number: str
    total_seats: int
    bus_type: str = "VIP"
    features: Optional[Union[list[str], dict[str, Any]]] = None
    is_active: bool = True


class BusCreate(BusBase):
    pass


class BusUpdate(BaseModel):
    company_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    bus_image_url: Optional[str] = None
    bus_number: Optional[str] = None
    total_seats: Optional[int] = None
    bus_type: Optional[str] = None
    features: Optional[Union[list[str], dict[str, Any]]] = None
    is_active: Optional[bool] = None

class BusResponse(BusBase):
    id: uuid.UUID
    company: Optional[BusCompanyResponse] = None
    created_at: datetime
    updated_at: datetime

    
    model_config = ConfigDict(from_attributes=True)