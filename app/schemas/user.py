import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
from app.schemas.rbac import RoleResponse



class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone_number: Optional[str] = None
    account_type: str = "customer"


class UserCreate(UserBase):
    password: str
    confirm_password: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    account_type: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    password: Optional[str] = None


class UserWithRolesResponse(BaseModel):
    id: uuid.UUID
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    is_active: bool
    is_superuser: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    
    roles: List[RoleResponse] = []


class UserResponse(UserBase):
    id: uuid.UUID
    is_superuser: bool
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    roles: List[str] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator("roles", mode="before")
    @classmethod
    def extract_role_names(cls, v: Any) -> List[str]:
        if not v:
            return []
        
        # SQLAlchemy Relationship မှ Object list ဝင်လာပါက role.name များကို သီးသန့်ထုတ်ယူမည်
        result = []
        for role in v:
            if isinstance(role, str):
                result.append(role)
            elif hasattr(role, "name"):
                result.append(role.name)
        return result