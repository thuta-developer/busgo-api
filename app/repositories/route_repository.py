import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.route import Route
from app.schemas.route import RouteCreate, RouteUpdate


class RouteRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Route], int]:
        query = select(Route)

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Route.origin.ilike(search_filter),
                    Route.destination.ilike(search_filter),
                )
            )

        if is_active is not None:
            query = query.where(Route.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * size
        query = query.order_by(Route.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, route_id: uuid.UUID) -> Optional[Route]:
        stmt = select(Route).where(Route.id == route_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_origin_destination(
        self, origin: str, destination: str
    ) -> Optional[Route]:
        """Find a route by origin and destination (case-insensitive)."""
        stmt = select(Route).where(
            and_(
                func.lower(Route.origin) == origin.lower(),
                func.lower(Route.destination) == destination.lower(),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: RouteCreate) -> Route:
        route = Route(**data.model_dump())
        self.db.add(route)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(
                f"A route from '{data.origin}' to '{data.destination}' already exists"
            )
        await self.db.refresh(route)
        return route

    async def update(self, route: Route, data: RouteUpdate) -> Route:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(route, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(
                f"A route from '{route.origin}' to '{route.destination}' already exists"
            )
        await self.db.refresh(route)
        return route

    async def delete(self, route: Route) -> None:
        await self.db.delete(route)
        await self.db.commit()