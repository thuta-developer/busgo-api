import uuid
from datetime import datetime, date, time
from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct

from app.api.deps import get_db, has_permission
from app.schemas.trip import TripCreate, TripUpdate, TripResponse
from app.models.trip import Trip
from app.schemas.common import PaginatedResponse
from app.services.trip_service import TripService

router = APIRouter(prefix="/trips", tags=["Trip Management"])


@router.get(
    "/",
    response_model=PaginatedResponse[TripResponse],
    dependencies=[Depends(has_permission("trip:read"))],
)
async def list_trips(
    search: Optional[str] = Query(None, description="Search by route or bus"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    include_bookable_only: bool = Query(
        True, description="Only show bookable schedules"
    ),
    route_id: Optional[uuid.UUID] = Query(None, description="Filter by route ID"),
    bus_id: Optional[uuid.UUID] = Query(None, description="Filter by bus ID"),
    origin: Optional[str] = Query(None, description="Filter by route origin"),
    destination: Optional[str] = Query(None, description="Filter by route destination"),
    travel_date: Optional[date] = Query(None, description="Filter by travel date"),
    user_type: str = Query("local", description="Price user type: local or foreigner"),
    time_of_day: Optional[str] = Query(
        None, description="Filter by time of day: morning, afternoon, night"
    ),
    db: AsyncSession = Depends(get_db),
):
    service = TripService(db)
    return await service.list_trips(
        search=search,
        is_active=is_active,
        page=page,
        size=size,
        route_id=route_id,
        bus_id=bus_id,
        origin=origin,
        destination=destination,
        departure_date=travel_date,
        user_type=user_type,
        include_bookable_only=include_bookable_only,
        time_of_day=time_of_day,
    )


@router.get(
    "/{trip_id}",
    response_model=TripResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("trip:read"))],
)
async def get_trip(trip_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = TripService(db)
    return await service.get_trip_by_id(trip_id)


@router.post(
    "/",
    response_model=TripResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("trip:create"))],
)
async def create_trip(data: TripCreate, db: AsyncSession = Depends(get_db)):
    service = TripService(db)
    return await service.create_trip(data)


@router.put(
    "/{trip_id}",
    response_model=TripResponse,
    dependencies=[Depends(has_permission("trip:update"))],
)
async def update_trip(
    trip_id: uuid.UUID, data: TripUpdate, db: AsyncSession = Depends(get_db)
):
    service = TripService(db)
    return await service.update_trip(trip_id, data)


@router.delete(
    "/{trip_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("trip:delete"))],
)
async def delete_trip(trip_id: uuid.UUID, hard_delete: bool = Query(False, description="Permanently delete (default: soft delete)") ,db: AsyncSession = Depends(get_db)):
    service = TripService(db)
    if hard_delete:
        await service.delete_trip(trip_id)
    else:
        await service.soft_trip_delete(trip_id)

    return {
        "message": f"Trip {'hard ' if hard_delete else 'soft '}deleted successfully"
    }
    