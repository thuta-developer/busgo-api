import uuid
import math
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.role_repository import RoleRepository
from app.repositories.permission_repository import PermissionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.common import PaginatedResponse
from app.schemas.rbac import RoleCreate, RoleUpdate, RoleResponse, RoleAssignPermissions
from app.schemas.user import UserResponse


class RoleService:
    def __init__(self, db: AsyncSession):
        self.role_repo = RoleRepository(db)
        self.perm_repo = PermissionRepository(db)
        self.user_repo = UserRepository(db)

    async def create_role(self, role_in: RoleCreate) -> RoleResponse:
        existing = await self.role_repo.get_by_name(role_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role '{role_in.name}' already exists",
            )

        role_data = role_in.model_dump()
        permission_ids = role_data.pop("permission_ids", [])

        role = await self.role_repo.create(role_data)

        if permission_ids:
            permissions = await self.perm_repo.get_by_ids(permission_ids)
            role = await self.role_repo.update_role_permissions(role, permissions)

        return RoleResponse.model_validate(role)

    async def get_roles_list(
        self, search: Optional[str], page: int, size: int
    ) -> PaginatedResponse[RoleResponse]:
        roles, total = await self.role_repo.get_paginated_roles(search=search, page=page, size=size)
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [RoleResponse.model_validate(r) for r in roles]
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def get_role_by_id(self, role_id: uuid.UUID) -> RoleResponse:
        role = await self.role_repo.get_by_id_with_permissions(role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return RoleResponse.model_validate(role)

    async def assign_permissions_to_role(
        self, role_id: uuid.UUID, data: RoleAssignPermissions
    ) -> RoleResponse:
        role = await self.role_repo.get_by_id_with_permissions(role_id)
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

        permissions = await self.perm_repo.get_by_ids(data.permission_ids)
        updated_role = await self.role_repo.update_role_permissions(role, permissions)
        return RoleResponse.model_validate(updated_role)

    async def assign_roles_to_user(
        self, user_id: uuid.UUID, role_ids: List[uuid.UUID]
    ) -> UserResponse:
        user = await self.user_repo.get_by_id_with_relations(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        roles = await self.role_repo.get_by_ids(role_ids)
        user.roles = roles
        self.role_repo.db.add(user)
        await self.role_repo.db.commit()
        await self.role_repo.db.refresh(user)

        return UserResponse.model_validate(user)

    async def delete_role(self, role_id: uuid.UUID) -> dict:
        success = await self.role_repo.delete(role_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        return {"message": "Role deleted successfully"}