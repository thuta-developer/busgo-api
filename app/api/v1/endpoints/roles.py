import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.schemas.common import PaginatedResponse
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, RoleAssignPermissions
from app.schemas.user import UserResponse
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["Roles Management"])


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(has_permission("role:create"))])
async def create_role(role_in: RoleCreate, db: AsyncSession = Depends(get_db)):
    service = RoleService(db)
    return await service.create_role(role_in)


@router.get(
    "/",
    response_model=PaginatedResponse[RoleResponse],
    dependencies=[Depends(has_permission("role:read"))],
)
async def list_roles(
    search: Optional[str] = Query(None, description="Search name or description"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = RoleService(db)
    return await service.get_roles_list(search=search, page=page, size=size)


@router.get(
    "/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(has_permission("role:read"))],
)
async def get_role_by_id(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = RoleService(db)
    return await service.get_role_by_id(role_id=role_id)


@router.post(
    "/{role_id}/permissions",
    response_model=RoleResponse,
    dependencies=[Depends(has_permission("role:update"))],
)
async def assign_permissions_to_role(
    role_id: uuid.UUID, data: RoleAssignPermissions, db: AsyncSession = Depends(get_db)
):
    """
    Role တစ်ခုထဲသို့ Permissions များကို Dynamic Assign ချိတ်ပေးခြင်း
    """
    service = RoleService(db)
    return await service.assign_permissions_to_role(role_id, data)



@router.post(
    "/users/{user_id}/assign-roles",
    response_model=UserResponse,
    dependencies=[Depends(has_permission("user:update"))],
)
async def assign_roles_to_user(
    user_id: uuid.UUID, role_ids: list[uuid.UUID], db: AsyncSession = Depends(get_db)
):
    """
    User တစ်ယောက်ထဲသို့ Roles များ Dynamic Assign ချိတ်ပေးခြင်း
    """
    service = RoleService(db)
    return await service.assign_roles_to_user(user_id, role_ids)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("role:delete"))],
)
async def delete_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = RoleService(db)
    return await service.delete_role(role_id)