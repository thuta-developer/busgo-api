import uuid
import math
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.route_repository import RouteRepository
from app.schemas.route import RouteCreate, RouteUpdate, RouteResponse
from app.schemas.common import PaginatedResponse


class RouteService:
    def __init__(self, db: AsyncSession):
        self.repo = RouteRepository(db)

    async def get_all_routes(
        self,
        search: Optional[str] = None,
        page: int = 1,
        size: int = 20,
        is_active: Optional[bool] = None,
    ) -> PaginatedResponse[RouteResponse]:
        routes, total = await self.repo.get_all(
            search=search,
            page=page,
            size=size,
            is_active=is_active,
        )

        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [RouteResponse.model_validate(r) for r in routes]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    async def get_route_by_id(self, route_id: uuid.UUID) -> RouteResponse:
        route = await self.repo.get_by_id(route_id)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found",
            )
        return RouteResponse.model_validate(route)

    async def create_route(self, data: RouteCreate) -> RouteResponse:
        # Check for duplicate route (case-insensitive)
        existing = await self.repo.get_by_origin_destination(
            data.origin, data.destination
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A route from '{data.origin}' to '{data.destination}' already exists",
            )

        try:
            route = await self.repo.create(data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        return RouteResponse.model_validate(route)

    async def update_route(
        self, route_id: uuid.UUID, update_data: RouteUpdate
    ) -> RouteResponse:
        route = await self.repo.get_by_id(route_id)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found",
            )

        # Determine the resulting origin/destination after update
        new_origin = update_data.origin if update_data.origin is not None else route.origin
        new_destination = (
            update_data.destination
            if update_data.destination is not None
            else route.destination
        )

        # Check for duplicate route (case-insensitive), excluding the current route
        existing = await self.repo.get_by_origin_destination(
            new_origin, new_destination
        )
        if existing and existing.id != route_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A route from '{new_origin}' to '{new_destination}' already exists",
            )

        try:
            updated = await self.repo.update(route, update_data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        return RouteResponse.model_validate(updated)

    async def delete_route(self, route_id: uuid.UUID) -> dict:
        """Route ဖျက်ထုတ်ခြင်း"""
        route = await self.repo.get_by_id(route_id)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found",
            )
        await self.repo.delete(route)
        # return {"message": "Route deleted successfully"}

    async def soft_route_delete(self, route_id: uuid.UUID) -> dict:
        route = await self.repo.get_by_id(route_id)
        if not route:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Route not found",
            )
        await self.repo.soft_route_delete(route)
        # return {"message": "Route deleted successfully"}


        