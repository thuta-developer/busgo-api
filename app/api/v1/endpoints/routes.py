import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct

from app.api.deps import get_db, has_permission
from app.schemas.route import RouteCreate, RouteUpdate, RouteResponse
from app.models.route import Route
from app.schemas.common import PaginatedResponse
from app.services.route_service import RouteService

router = APIRouter(prefix="/routes", tags=["Routes Management"])


@router.get(
    "/",
    response_model=PaginatedResponse[RouteResponse],
    dependencies=[Depends(has_permission("route:read"))],
)
async def list_routes(
    search: Optional[str] = Query(None, description="Search by name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = RouteService(db)
    return await service.get_all_routes(
        search=search,
        is_active=is_active,
        page=page,
        size=size,
    )

@router.get(
    "/{route_id}",
    response_model=RouteResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("route:read"))],
)
async def get_route(route_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = RouteService(db)
    return await service.get_route_by_id(route_id)


@router.post(
    "/",
    response_model=RouteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("route:create"))],
)
async def create_route(data: RouteCreate, db: AsyncSession = Depends(get_db)):
    service = RouteService(db)
    return await service.create_route(data)


@router.put(
    "/{route_id}",
    response_model=RouteResponse,
    dependencies=[Depends(has_permission("route:update"))],
)
async def update_route(
    route_id: uuid.UUID, data: RouteUpdate, db: AsyncSession = Depends(get_db)
):
    service = RouteService(db)
    return await service.update_route(route_id, data)


@router.delete(
    "/{route_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("route:delete"))],
)
async def delete_route(route_id: uuid.UUID, hard_delete: bool = Query(False, description="Permanently delete (default: soft delete)") ,db: AsyncSession = Depends(get_db)):
    service = RouteService(db)
    if hard_delete:
        await service.delete_route(route_id)
    else:
        await service.soft_route_delete(route_id)

    return {
        "message": f"Route {'hard ' if hard_delete else 'soft '}deleted successfully"
    }



@router.get(
    "/cities/origins",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get all unique origins",
)
async def get_origins(
    db: AsyncSession = Depends(get_db)
):
    service = RouteService(db)
    stmt = select(distinct(Route.origin)).where(Route.is_active == True)
    result = await db.execute(stmt)
    origins = result.scalars().all()

    return {"data": origins}

@router.get(
    "/cities/destinations",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="Get all unique destinations",
)
async def get_destinations(
    db: AsyncSession = Depends(get_db)
):
    service = RouteService(db)
    stmt = select(distinct(Route.destination)).where(Route.is_active == True)
    result = await db.execute(stmt)
    destinations = result.scalars().all()

    return {"data": destinations}
