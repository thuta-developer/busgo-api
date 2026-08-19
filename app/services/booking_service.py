import uuid
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.booking import Booking, BookingStatus
from app.models.booking_seat import BookingSeat
from app.models.trip_seat import TripSeat, TripSeatStatus
from app.repositories.booking_repository import BookingRepository
from app.repositories.trip_seat_repository import TripSeatRepository
from app.repositories.trip_repository import TripRepository

from app.repositories.bus_repository import BusRepository
from app.schemas.booking import (
    BookingCreate,
    BookingUpdate,
    BookingResponse,
    BookingWithPaymentRequest,
    BookingWithPaymentResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.payment_service import PaymentService
from app.services.trip_seat_service import TripSeatService
from app.schemas.trip_seat import BulkHoldRequest
from app.schemas.booking import BookingSeatResponse


logger = logging.getLogger(__name__)


class BookingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BookingRepository(db)
        self.trip_seat_repo = TripSeatRepository(db)
        self.trip_repo = TripRepository(db)
        self.payment_service = PaymentService(db)
        self.trip_seat_service = TripSeatService(db)

    # ==============================================
    # Helper Methods
    # ==============================================
    def _generate_booking_code(self) -> str:
        import random
        now = datetime.now(timezone.utc)
        return f"BusGo-{now.strftime('%Y')}-{random.randint(100000, 999999)}"

    def _calculate_expiry(self) -> datetime:
        """Booking Expiry Date တွက်ခြင်း"""
        return datetime.now(timezone.utc) + timedelta(minutes=settings.BOOKING_EXPIRY_MINUTES)

    async def _get_trip_seat_price(
        self,
        trip_id: uuid.UUID,
    ) -> Decimal:
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found")
        
        return trip.local_price

    async def _to_response(
    self,
    booking: Booking,
    include_payment_status: bool = True,
    ) -> BookingResponse:
        # Convert booking to response
        response = BookingResponse.model_validate(booking)
        if booking.booking_seats:
            response.booking_seats = [
                BookingSeatResponse.model_validate(seat) 
                for seat in booking.booking_seats
            ]
        
        if include_payment_status and getattr(booking, "payments", None):
            response.payment_status = booking.payments[0].status.value
        return response

    # ==============================================
    # Create Booking (With Payment)
    # ==============================================
    
    async def create_booking_with_payment(
        self,
        user_id: uuid.UUID,
        data: BookingWithPaymentRequest,
    ) -> BookingWithPaymentResponse:
        """
        Booking ဖန်တီးပြီး Payment ကို တစ်ခါတည်း စတင်ခြင်း
        Flow:
        1. Trip ရှိမရှိ စစ်ဆေးခြင်း
        2. Selected Seats တွေကို Bulk Hold လုပ်ခြင်း
        3. Booking Record ဖန်တီးခြင်း
        4. BookingSeat Records ဖန်တီးခြင်း
        5. Payment Initiate လုပ်ခြင်း
        6. Response ပြန်ပေးခြင်း
        """
        trip = await self.trip_repo.get_by_id(data.trip_id)
        if not trip or not trip.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trip not found or inactive."
            )

        user_type = getattr(data, "user_type", "local")
        travel_date = data.travel_date
        
        hold_payload = BulkHoldRequest(travel_date=travel_date, seat_ids=data.seat_ids)
        held_result = await self.trip_seat_service.bulk_hold_seats(
            trip_id=data.trip_id,
            payload=hold_payload,
            user_id=user_id,
        )
        held_seats = held_result.seats

        if not held_seats or len(held_seats) != len(data.seat_ids):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="One or more seats are not available. Please refresh and try again."
            )

        try:
            total_amount = Decimal(0)
            booking_seats_list = []

            # 3. Dynamic Price Computation based on travel_date & user_type
            for seat in held_seats:
                seat_price = seat.price  # TripSeatService bulk_hold တွင် တွက်ချက်ပေးပြီးဖြစ်သည်
                total_amount += seat_price

                booking_seats_list.append(
                    BookingSeat(
                        trip_seat_id=seat.id,
                        seat_number=seat.seat_number or "N/A",
                        row_number=seat.row_number or 0,
                        column_number=seat.column_number or 0,
                        position=seat.position or "UNKNOWN",
                        price_at_booking=seat_price,
                        quantity=1,
                    )
                )

            net_amount = total_amount

            # Create Booking
            booking = Booking(
                user_id=user_id,
                trip_id=data.trip_id,
                booking_code=self._generate_booking_code(),
                status=BookingStatus.PENDING,
                total_seats=len(booking_seats_list),
                name=data.name,
                email=data.email,
                phone=data.phone,
                gender=data.gender,
                special_request=data.special_request,
                total_amount=total_amount,
                service_fee=Decimal("0.0"),
                discount_amount=Decimal("0.0"),
                net_amount=net_amount,
                booking_date=datetime.now(timezone.utc),
                expiry_date=self._calculate_expiry(),
                travel_date=travel_date,
                booking_seats=booking_seats_list
            )
            booking = await self.repo.create(booking)

            payment_response = await self.payment_service.initiate_payment(
                booking_id=booking.id,
                payment_method=data.payment_method,
                return_url=str(data.return_url) if data.return_url else None,
                cancel_url=str(data.cancel_url) if data.cancel_url else None,
            )

            booking_updated = await self.repo.get_by_id(booking.id)
            return BookingWithPaymentResponse(
                booking=await self._to_response(booking_updated),
                payment=payment_response,
            )
            
        except Exception as e:
            logger.error(f"Booking failed: {str(e)}")
            await self.db.rollback()
            await self.trip_seat_repo.bulk_release_hold_seats(
                trip_id=data.trip_id,
                travel_date=travel_date,
                seat_ids=[s.id for s in held_seats],
                user_id=user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Booking creation failed: {str(e)}"
            )

    # ==============================================
    # Get Bookings
    # ==============================================
    
    async def get_booking_by_id(
        self,
        booking_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> BookingResponse:
        """Booking ID ဖြင့် ရှာဖွေခြင်း"""
        booking = await self.repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        # Check authorization (user can only view their own bookings unless admin)
        if user_id and booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this booking"
            )
        
        return await self._to_response(booking)

    async def get_user_bookings(self, user_id: uuid.UUID, status: Optional[BookingStatus] = None, page: int = 1, size: int = 20) -> PaginatedResponse[BookingResponse]:
        bookings, total = await self.repo.get_by_user_id(user_id=user_id, status=status, page=page, size=size)
        items = [await self._to_response(b) for b in bookings]
        return PaginatedResponse(items=items, total=total, page=page, size=size, total_pages=(total + size - 1) // size if total else 0)

    
    async def get_trip_bookings(
        self,
        trip_id: uuid.UUID,
        status: Optional[BookingStatus] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[BookingResponse]:
        """Trip အတွက် Booking စာရင်းကို ပြန်ပေးခြင်း (Admin)"""
        bookings, total = await self.repo.get_by_trip_id(
            trip_id=trip_id,
            status=status,
            page=page,
            size=size,
        )
        
        items = [await self._to_response(b) for b in bookings]
        total_pages = (total + size - 1) // size if total > 0 else 0
        
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    # ==============================================
    # Update Booking
    # ==============================================
    
    async def update_booking(
        self,
        booking_id: uuid.UUID,
        data: BookingUpdate,
        user_id: uuid.UUID,
    ) -> BookingResponse:
        """Booking အချက်အလက် ပြင်ဆင်ခြင်း"""
        booking = await self.repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check authorization
        if booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this booking"
            )
        
        # Can't update if booking is already confirmed or cancelled
        if booking.status in [BookingStatus.CONFIRMED, BookingStatus.CANCELLED, BookingStatus.REFUNDED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update booking with status: {booking.status}"
            )
        
        booking = await self.repo.update(booking, data)
        return await self._to_response(booking)

    # ==============================================
    # Cancel Booking
    # ==============================================
    
    async def cancel_booking(
        self,
        booking_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> dict:
        """Booking ကို ပယ်ဖျက်ခြင်း"""
        booking = await self.repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        
        # Check authorization
        if booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to cancel this booking"
            )
        
        # Can only cancel pending bookings
        if booking.status not in [BookingStatus.PENDING, BookingStatus.AWAITING_PAYMENT]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel booking with status: {booking.status}"
            )
        
        # Update booking status
        booking.status = BookingStatus.CANCELLED
        await self.db.commit()
        
        # Release held seats (if any)
        for booking_seat in booking.booking_seats:
            await self.trip_seat_repo.bulk_release_hold_seats(
                trip_id=booking.trip_id,
                seat_ids=[booking_seat.trip_seat_id],
                user_id=user_id,
            )
        
        return {
            "message": "Booking cancelled successfully",
            "booking_id": str(booking.id),
            "booking_code": booking.booking_code,
        }

    # ==============================================
    # Admin: Update Booking Status
    # ==============================================
    
    async def admin_update_status(
        self,
        booking_id: uuid.UUID,
        status: BookingStatus,
    ) -> BookingResponse:
        """Admin က Booking Status ကို ပြင်ဆင်ခြင်း"""
        booking = await self.repo.update_status(booking_id, status)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        return await self._to_response(booking)

    # ==============================================
    # Background: Cleanup Expired Bookings
    # ==============================================
    
    async def cleanup_expired_bookings(self) -> int:
        expired_bookings = await self.repo.get_expired_bookings()
        expired_count = 0
        for booking in expired_bookings:
            booking.status = BookingStatus.EXPIRED
            for seat in booking.booking_seats:
                await self.trip_seat_repo.bulk_release_hold_seats(
                    trip_id=booking.trip_id,
                    travel_date=booking.travel_date,
                    seat_ids=[seat.trip_seat_id],
                    user_id=booking.user_id,
                )
            expired_count += 1
        await self.db.commit()
        return expired_count


            



        
