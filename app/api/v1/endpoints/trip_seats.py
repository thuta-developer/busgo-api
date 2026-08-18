import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission, get_current_user
from app.models.user import User
from app.schemas.trip_seat import TripSeatResponse, TripSeatBulkResponse
from app.models.trip_seat import TripSeatStatus
from app.services.trip_seat_service import TripSeatService

router = APIRouter(prefix="/trips/{trip_id}/seats", tags=["Trip Seats"])


@router.get(
    "/",
    response_model=list[TripSeatResponse],
    dependencies=[Depends(has_permission("trip:read"))],
)
async def get_trip_seats(
    trip_id: uuid.UUID,
    status: Optional[TripSeatStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
):
    service = TripSeatService(db)
    return await service.get_trip_seats(trip_id, status)


@router.post(
    "/initialize",
    response_model=list[TripSeatResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("trip:update"))],
)
async def initialize_trip_seats(
    trip_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    # This endpoint can be called manually or automatically after trip creation.
    # We'll need to get the bus_id from the trip.
    from app.repositories.trip_repository import TripRepository
    trip_repo = TripRepository(db)
    trip = await trip_repo.get_by_id(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    service = TripSeatService(db)
    return await service.initialize_trip_seats(trip_id, trip.bus_id)


@router.post(
    "/{seat_id}/book",
    response_model=TripSeatResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:create"))],
)
async def book_seat(
    trip_id: uuid.UUID,
    seat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TripSeatService(db)
    return await service.book_seat(trip_id, seat_id, current_user.id)


@router.post(
    "/{trip_seat_id}/cancel",
    response_model=TripSeatResponse,
    dependencies=[Depends(has_permission("booking:update"))],
)
async def cancel_booking(
    trip_seat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = TripSeatService(db)
    return await service.cancel_booking(trip_seat_id, current_user.id)


@router.post(
    "/{seat_id}/hold",
    response_model=TripSeatResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:create"))],
)
async def hold_seat(
    trip_id: uuid.UUID,
    seat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ထိုင်ခုံကို ခဏတာ (10 မိနစ်) သိမ်းဆည်းထားသည်။ 
    ဤ API ကို ထိုင်ခုံရွေးပြီး Payment Page သွားခါနီးတွင် ခေါ်ပါ။
    """
    service = TripSeatService(db)
    return await service.hold_seat(trip_id, seat_id, current_user.id)

@router.post(
    "/{seat_id}/confirm",
    response_model=TripSeatResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:create"))],
)
async def confirm_booking(
    trip_id: uuid.UUID,
    seat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hold ထားသော ထိုင်ခုံကို အပြီးအပိုင် ကြိုတင်မှာယူအတည်ပြုသည်။
    (Payment Success ဖြစ်ပြီးမှသာ ခေါ်ပါ)
    """
    service = TripSeatService(db)
    return await service.confirm_booking(trip_id, seat_id, current_user.id)


@router.post(
    "/{seat_id}/release",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:update"))],
)
async def release_hold(
    trip_id: uuid.UUID,
    seat_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hold ကို ပြန်လွှတ်သည် (ဥပမာ - Payment ပျက်ကျခြင်း၊ နောက်ပြန်ဆုတ်ခြင်း)
    """
    service = TripSeatService(db)
    return await service.release_hold(trip_id, seat_id, current_user.id)