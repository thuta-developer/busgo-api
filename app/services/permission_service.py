import uuid
import math
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.permission_repository import PermissionRepository
from app.schemas.common import PaginatedResponse
from app.schemas.rbac import PermissionCreate, PermissionUpdate, PermissionResponse


class PermissionService:
    def __init__(self, db: AsyncSession):
        self.perm_repo = PermissionRepository(db)

    async def create_permission(self, perm_in: PermissionCreate) -> PermissionResponse:
        existing = await self.perm_repo.get_by_name(perm_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Permission '{perm_in.name}' already exists",
            )
        perm = await self.perm_repo.create(perm_in.model_dump())
        return PermissionResponse.model_validate(perm)

    async def get_permissions_list(
        self, search: Optional[str], module: Optional[str], page: int, size: int
    ) -> PaginatedResponse[PermissionResponse]:
        perms, total = await self.perm_repo.get_paginated_permissions(
            search=search, module=module, page=page, size=size
        )
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [PermissionResponse.model_validate(p) for p in perms]
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def update_permission(
        self, perm_id: uuid.UUID, perm_in: PermissionUpdate
    ) -> PermissionResponse:
        perm = await self.perm_repo.get_by_id(perm_id)
        if not perm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

        updated = await self.perm_repo.update(perm, perm_in.model_dump(exclude_unset=True))
        return PermissionResponse.model_validate(updated)

    async def delete_permission(self, perm_id: uuid.UUID) -> dict:
        success = await self.perm_repo.delete(perm_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")
        return {"message": "Permission deleted successfully"}