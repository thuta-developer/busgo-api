import uuid
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rbac import Permission
from app.repositories.base import BaseRepository

class PermissionRepository(BaseRepository[Permission]):
    def __init__(self, db: AsyncSession):
        super().__init__(Permission, db)

    async def get_by_name(self, name: str) -> Optional[Permission]:
        stmt = select(self.model).where(self.model.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_ids(self, permission_ids: List[uuid.UUID]) -> List[Permission]:
        stmt = select(Permission).where(Permission.id.in_(permission_ids))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_paginated_permissions(
        self,
        search: Optional[str] = None,
        module: Optional[str] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[Permission], int]:
        query = select(Permission)

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Permission.name.ilike(search_filter),
                    Permission.description.ilike(search_filter),
                )
            )

        if module:
            query = query.where(Permission.module == module)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Pagination Offset
        offset = (page - 1) * size
        query = query.order_by(Permission.module.asc(), Permission.name.asc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total
