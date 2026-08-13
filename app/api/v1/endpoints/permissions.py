import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.schemas.common import PaginatedResponse
from app.schemas.rbac import PermissionCreate, PermissionUpdate, PermissionResponse
from app.services.permission_service import PermissionService

router = APIRouter(prefix="/permissions", tags=["Permissions Management"])



@router.post(
    "/",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("permission:create"))]
)
async def create_permission(perm_in: PermissionCreate, db : AsyncSession = Depends(get_db)):
    service = PermissionService(db)
    return await service.create_permission(perm_in)


@router.get(
    "/",
    response_model=PaginatedResponse[PermissionResponse],
    dependencies=[Depends(has_permission("permission:read"))],
)
async def list_permissions(
    search: Optional[str] = Query(None, description="Search name or description"),
    module: Optional[str] = Query(None, description="Filter by module e.g., 'Bus'"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = PermissionService(db)
    return await service.get_permissions_list(search=search, module=module, page=page, size=size)



@router.put(
    "/{perm_id}",
    response_model=PermissionResponse,
    dependencies=[Depends(has_permission("permission:update"))],
)
async def update_permission(
    perm_id: uuid.UUID, perm_in: PermissionUpdate, db: AsyncSession = Depends(get_db)
):
    service = PermissionService(db)
    return await service.update_permission(perm_id, perm_in)


@router.delete(
    "/{perm_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("permission:delete"))],
)
async def delete_permission(perm_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = PermissionService(db)
    return await service.delete_permission(perm_id)