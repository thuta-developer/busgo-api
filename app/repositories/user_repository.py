import uuid
from typing import Optional, Tuple, List
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.rbac import Role
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.email == email)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone_number(self, phone_number: str) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.phone_number == phone_number)
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_by_id_with_relations(self, user_id: uuid.UUID) -> Optional[User]:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .where(User.id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_paginated_users(
        self,
        search: Optional[str] = None,
        account_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 10,
    ) -> Tuple[List[User], int]:
        query = select(User).options(selectinload(User.roles))

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    User.full_name.ilike(search_filter),
                    User.email.ilike(search_filter),
                    User.phone_number.ilike(search_filter),
                )
            )

        if account_type:
            query = query.where(User.account_type == account_type)

        if is_active is not None:
            query = query.where(User.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Pagination Offset
        offset = (page - 1) * size
        query = query.order_by(User.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        users = result.scalars().all()

        return list(users), total