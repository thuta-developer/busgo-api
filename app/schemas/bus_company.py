import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import datetime

class BusCompanyBase(BaseModel):
    name: str
    contact_phone: str
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: bool = True


class BusCompanyCreate(BusCompanyBase):
    pass


class BusCompanyUpdate(BaseModel):
    name: Optional[str] = None
    contact_phone: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    logo_url: Optional[str] = None
    is_active: Optional[bool] = None


class BusCompanyResponse(BusCompanyBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)