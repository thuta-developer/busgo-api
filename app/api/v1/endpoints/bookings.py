import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission, get_current_user
from app.models.user import User
from app.models.booking import BookingStatus
from app.schemas.booking import (
    BookingResponse,
    BookingUpdate,
    BookingWithPaymentRequest,
    BookingWithPaymentResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.booking_service import BookingService

router = APIRouter(prefix="/bookings", tags=["Bookings"])



@router.post(
    "/with-payment",
    response_model=BookingWithPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("booking:create"))],
)
async def create_booking_with_payment(
    data: BookingWithPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = BookingService(db)
    return await service.create_booking_with_payment(current_user.id, data=data)


@router.get(
    "/me",
    response_model=PaginatedResponse[BookingResponse],
    dependencies=[Depends(has_permission("booking:read"))],
)
async def get_my_bookings(
    status: Optional[BookingStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    မိမိ၏ Booking စာရင်းကို ပြန်ပေးခြင်း
    """
    service = BookingService(db)
    return await service.get_user_bookings(
        user_id=current_user.id,
        status=status,
        page=page,
        size=size,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    dependencies=[Depends(has_permission("booking:read"))],
)
async def get_booking(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Booking အသေးစိတ်ကို ပြန်ပေးခြင်း
    """
    service = BookingService(db)
    return await service.get_booking_by_id(
        booking_id=booking_id,
        user_id=current_user.id,
    )



@router.put(
    "/{booking_id}",
    response_model=BookingResponse,
    dependencies=[Depends(has_permission("booking:update"))],
)
async def update_booking(
    booking_id: uuid.UUID,
    data: BookingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Booking အချက်အလက် ပြင်ဆင်ခြင်း (User Info သာ)
    """
    service = BookingService(db)
    return await service.update_booking(
        booking_id=booking_id,
        data=data,
        user_id=current_user.id,
    )


@router.post(
    "/{booking_id}/cancel",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("booking:update"))],
)
async def cancel_booking(
    booking_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Booking ကို ပယ်ဖျက်ခြင်း
    """
    service = BookingService(db)
    return await service.cancel_booking(
        booking_id=booking_id,
        user_id=current_user.id,
    )


@router.get(
    "/trip/{trip_id}",
    response_model=PaginatedResponse[BookingResponse],
    dependencies=[Depends(has_permission("booking:read_admin"))],
)
async def get_trip_bookings(
    trip_id: uuid.UUID,
    status: Optional[BookingStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Trip တစ်ခုအတွက် Booking စာရင်းကို ပြန်ပေးခြင်း (Admin Only)
    """
    service = BookingService(db)
    return await service.get_trip_bookings(
        trip_id=trip_id,
        status=status,
        page=page,
        size=size,
    )


@router.post(
    "/{booking_id}/admin-status",
    response_model=BookingResponse,
    dependencies=[Depends(has_permission("booking:update_admin"))],
)
async def admin_update_booking_status(
    booking_id: uuid.UUID,
    status: BookingStatus,
    db: AsyncSession = Depends(get_db),
):
    """
    Admin က Booking Status ကို ပြင်ဆင်ခြင်း
    """
    service = BookingService(db)
    return await service.admin_update_status(booking_id, status)


@router.post(
    "/cleanup-expired",
    response_model=dict,
    dependencies=[Depends(has_permission("booking:update_admin"))],
)
async def cleanup_expired_bookings(
    db: AsyncSession = Depends(get_db),
):
    """
    သက်တမ်းကုန်သွားသော PENDING Bookings များကို EXPIRED အဖြစ်ပြောင်းခြင်း (Admin Only)
    """
    service = BookingService(db)
    count = await service.cleanup_expired_bookings()
    return {
        "message": f"Cleaned up {count} expired bookings",
        "count": count,
    }