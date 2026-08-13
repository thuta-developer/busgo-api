import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None
    module: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass


class PermissionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    module: Optional[str] = None


class PermissionResponse(PermissionBase):
    id: uuid.UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# ROLE SCHEMAS
# ==========================================

class RoleBase(BaseModel):
    name: str  # e.g., 'Counter Staff', 'Gate Manager'
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: List[uuid.UUID] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class RoleResponse(RoleBase):
    id: uuid.UUID
    permissions: List[PermissionResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ==========================================
# ASSIGNMENT SCHEMAS
# ==========================================

class RoleAssignPermissions(BaseModel):
    permission_ids: List[uuid.UUID]


class UserAssignRoles(BaseModel):
    role_ids: List[uuid.UUID]