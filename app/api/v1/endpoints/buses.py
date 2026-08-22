import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.deps import get_db, has_permission
from app.schemas.bus import BusCreate, BusUpdate, BusResponse
from app.schemas.common import PaginatedResponse
from app.services.bus_service import BusService

router = APIRouter(prefix="/buses", tags=["Buses Management"])

@router.get(
    "/",
    response_model=PaginatedResponse[BusResponse],
    dependencies=[Depends(has_permission("bus:read"))],
)
async def list_buses(
    search: Optional[str] = Query(None, description="Search by name"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    
    service = BusService(db)
    return await service.get_all_buses(
        search=search,
        is_active=is_active,
        page=page,
        size=size,
    )


@router.get(
    "/{bus_id}",
    response_model=BusResponse,
    dependencies=[Depends(has_permission("bus:read"))],
)
async def get_bus(bus_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = BusService(db)
    return await service.get_bus_by_id(bus_id)


@router.post(
    "/",
    response_model=BusResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("bus:create"))],
)
async def create_bus(data: BusCreate, db: AsyncSession = Depends(get_db)):
    service = BusService(db)
    return await service.create_bus(data)


@router.put(
    "/{bus_id}",
    response_model=BusResponse,
    dependencies=[Depends(has_permission("bus:update"))],
)
async def update_bus(
    bus_id: uuid.UUID, data: BusUpdate, db: AsyncSession = Depends(get_db)
):
    service = BusService(db)
    return await service.update_bus(bus_id, data)


@router.delete(
    "/{bus_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("bus:delete"))],
)
async def delete_bus(bus_id: uuid.UUID, hard_delete: bool = Query(False, description="Permanently delete (default: soft delete)"), db: AsyncSession = Depends(get_db)):
    service = BusService(db)
    if hard_delete:
        await service.delete_bus(bus_id)
    else:
        await service.soft_delete_bus(bus_id)

    return {
        "message": f"Bus {'hard ' if hard_delete else 'soft '}deleted successfully"
    }


@router.post(
    "/{bus_id}/image",
    response_model = BusResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("bus:update"))],
)
async def upload_bus_image(
    bus_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    service = BusService(db)
    return await service.upload_bus_image(bus_id=bus_id, file=file)
