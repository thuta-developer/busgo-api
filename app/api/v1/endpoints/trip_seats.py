import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission, get_current_user
from app.models.user import User
from app.models.trip_seat import TripSeatStatus
from app.schemas.trip_seat import (
    TripSeatResponse,
    TripSeatBulkResponse,
    BulkHoldRequest,
    BulkBookRequest,
    BulkConfirmRequest,
    BulkReleaseRequest,
)
from app.services.trip_seat_service import TripSeatService

router = APIRouter(prefix="/trips/{trip_id}/seats", tags=["Trip Seats"])


@router.get(
    "/",
    response_model=list[TripSeatResponse],
    dependencies=[Depends(has_permission("trip:read"))],
)
async def get_trip_seats(
    trip_id: uuid.UUID,
    travel_date: date = Query(..., description="Travel date (YYYY-MM-DD)"),
    status: Optional[TripSeatStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
    user_type: Optional[str] = Query("local")
):
    """
    သတ်မှတ်ထားသော ရက်စွဲအလိုက် Trip ၏ ထိုင်ခုံများအားလုံးကို ရယူသည်။
    (ထိုရက်အတွက် DB တွင် DB Record မရှိသေးပါက Auto-generate ပြုလုပ်ပေးမည်)
    """
    service = TripSeatService(db)
    return await service.get_trip_seats(
        trip_id=trip_id, travel_date=travel_date, status_filter=status, user_type=user_type
    )


# ========== Bulk seat operations ==========


@router.post(
    "/bulk/hold",
    response_model=TripSeatBulkResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:create"))],
)
async def bulk_hold_seats(
    trip_id: uuid.UUID,
    payload: BulkHoldRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် Hold လုပ်သည်။
    Body: {"travel_date": "2026-08-25", "seat_ids": ["<seat_id_or_trip_seat_id>"]}
    """
    service = TripSeatService(db)
    return await service.bulk_hold_seats(trip_id, payload, current_user.id)


@router.post(
    "/bulk/book",
    response_model=TripSeatBulkResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:create"))],
)
async def bulk_book_seats(
    trip_id: uuid.UUID,
    payload: BulkBookRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် Direct Book လုပ်သည်။
    Body: {"travel_date": "2026-08-25", "seat_ids": ["<seat_id_or_trip_seat_id>"]}
    """
    service = TripSeatService(db)
    return await service.bulk_book_seats(trip_id, payload, current_user.id)


@router.post(
    "/bulk/confirm",
    response_model=TripSeatBulkResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:create"))],
)
async def bulk_confirm_booking(
    trip_id: uuid.UUID,
    payload: BulkConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hold ထားသော ထိုင်ခုံများကို အပြီးအပိုင် Confirmation (BOOKED) ပြုလုပ်သည်။
    Body: {"travel_date": "2026-08-25", "seat_ids": ["<seat_id_or_trip_seat_id>"]}
    """
    service = TripSeatService(db)
    return await service.bulk_confirm_booking(trip_id, payload, current_user.id)


@router.post(
    "/bulk/release",
    response_model=TripSeatBulkResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:update"))],
)
async def bulk_release_hold(
    trip_id: uuid.UUID,
    payload: BulkReleaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Hold ထားသော ထိုင်ခုံများကို ပြန်လွှတ် (Release) ပြုလုပ်သည်။
    Body: {"travel_date": "2026-08-25", "seat_ids": ["<seat_id_or_trip_seat_id>"]}
    """
    service = TripSeatService(db)
    return await service.bulk_release_hold(trip_id, payload, current_user.id)