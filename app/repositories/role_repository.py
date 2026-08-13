import uuid
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.rbac import Role, Permission
from app.repositories.base import BaseRepository

class RoleRepository(BaseRepository[Role]):
    def __init__(self, db: AsyncSession):
        super().__init__(Role, db)

    async def get_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_permissions(self, role_id: uuid.UUID) -> Optional[Role]:
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, role_ids: List[uuid.UUID]) -> List[Role]:
        stmt = select(Role).where(Role.id.in_(role_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated_roles(
        self,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[Role], int]:
        query = select(Role).options(selectinload(Role.permissions))

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Role.name.ilike(search_filter),
                    Role.description.ilike(search_filter),
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * size
        query = query.order_by(Role.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_role_permissions(self, role: Role, permissions: List[Permission]) -> Role:
        role.permissions = permissions
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role