import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission
from app.schemas.seat import BusSeatResponse, GenerateSeatsRequest
from app.services.seat_service import SeatService

router = APIRouter(prefix="/buses", tags=["Bus Seats Template Layout"])


@router.post(
    "/{bus_id}/generate-seats",
    response_model=List[BusSeatResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("bus:update"))],
)
async def generate_bus_seats(
    bus_id: uuid.UUID,
    payload: GenerateSeatsRequest,
    db: AsyncSession = Depends(get_db),
):
    service = SeatService(db)
    return await service.generate_bus_seats(bus_id=bus_id, payload=payload)

@router.get(
    "/{bus_id}/seats",
    response_model=List[BusSeatResponse],
    status_code=status.HTTP_200_OK,
)
async def get_bus_seats(
    bus_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    service = SeatService(db)
    return await service.get_bus_seats(bus_id=bus_id)