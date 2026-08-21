import uuid
import logging
from datetime import datetime, timezone, timedelta, time, date
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
    BookingPricePreviewRequest,
    BookingPricePreviewResponse,
    PricePreviewSeatItem,
)
from app.schemas.common import PaginatedResponse
from app.services.payment_service import PaymentService
from app.services.trip_seat_service import TripSeatService
from app.services.promo_service import PromotionService
from app.schemas.promotion import ApplyPromotionRequest
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
        self.promo_service = PromotionService(db)

    # ==============================================
    # Helper Methods
    # ==============================================
    def _generate_booking_code(self) -> str:
        import random

        now = datetime.now(timezone.utc)
        return f"BusGo-{now.strftime('%Y')}-{random.randint(100000, 999999)}"

    def _calculate_expiry(self) -> datetime:
        """Booking Expiry Date တွက်ခြင်း"""
        return datetime.now(timezone.utc) + timedelta(
            minutes=settings.BOOKING_EXPIRY_MINUTES
        )

    async def _get_trip_seat_price(
        self,
        trip_id: uuid.UUID,
    ) -> Decimal:
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise ValueError("Trip not found")

        return trip.local_price

    async def _compute_seat_price(
        self,
        trip,
        travel_date,
        user_type: str = "local",
    ) -> Decimal:
        """
        ထိုင်ခုံ တစ်ခုအတွက် သတ်မှတ်ရက် (Festival ဟုတ်/မဟုတ်) နှင့်
        User Type (local/foreigner) အပေါ်မူတည်၍ Price ကို ပြန်လည်တွက်ချက်ပေးခြင်း။
        """
        user_type = (user_type or "local").lower()

        # ၁။ travel_date ကို timezone-aware datetime အဖြစ် ပြောင်းပါ
        check_date = travel_date
        if isinstance(check_date, date) and not isinstance(check_date, datetime):
            check_date = datetime.combine(check_date, time.min, tzinfo=timezone.utc)

        # ၂။ Festival ရက် ဟုတ်မဟုတ် စစ်ဆေးပါ
        is_festival = False
        festival_start = getattr(trip, "festival_start_date", None)
        festival_end = getattr(trip, "festival_end_date", None)

        if festival_start and festival_end:
            if festival_start.tzinfo is None:
                festival_start = festival_start.replace(tzinfo=timezone.utc)
            if festival_end.tzinfo is None:
                festival_end = festival_end.replace(tzinfo=timezone.utc)

            if festival_start <= check_date <= festival_end:
                is_festival = True

        # ၃။ User Type အားလိုက် Base Price ရွေးချယ်ပါ
        regular_base_price = (
            trip.foreigner_price if user_type == "foreigner" else trip.local_price
        )
        festival_base_price = (
            trip.foreigner_festival_price
            if user_type == "foreigner"
            else trip.local_festival_price
        )

        # ၄။ Festival ရက်ဖြစ်ပြီး festival price ရှိလျှင် ထို price ကိုသုံးမည်
        if is_festival and festival_base_price is not None:
            return festival_base_price
        return regular_base_price or Decimal("0.0")

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
        3. Promo Code ရှိပါက Discount တွက်ချက်ခြင်း
        4. Booking Record ဖန်တီးခြင်း
        5. BookingSeat Records ဖန်တီးခြင်း
        6. Payment Initiate လုပ်ခြင်း
        7. Response ပြန်ပေးခြင်း
        """
        trip = await self.trip_repo.get_by_id(data.trip_id)
        if not trip or not trip.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trip not found or inactive.",
            )

        user_type = (getattr(data, "user_type", "local") or "local").lower()
        if user_type not in {"local", "foreigner"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="user_type must be either 'local' or 'foreigner'",
            )
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
                detail="One or more seats are not available. Please refresh and try again.",
            )

        try:
            total_amount = Decimal(0)
            booking_seats_list = []

            # 3. Compute the booking price from the trip pricing rules.
            for seat in held_seats:
                seat_price = await self._compute_seat_price(
                    trip=trip,
                    travel_date=travel_date,
                    user_type=user_type,
                )
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

            # ===== Promotion Handling (Validate AFTER total is computed) =====
            promotion = None
            discount_amount = Decimal("0.0")
            if data.promo_code:
                try:
                    # Validate promotion & recalculate discount with REAL total
                    promo_result = await self.promo_service.apply_promotion(
                        user_id=user_id,
                        data=type(
                            "ApplyPromotionRequest",
                            (),
                            {
                                "promo_code": data.promo_code,
                                "booking_total": float(total_amount),
                            },
                        )(),
                    )
                    promotion = await self.promo_service.repo.get_by_code(
                        data.promo_code
                    )
                    discount_amount = Decimal(
                        str(promo_result.discount_applied)
                    ).quantize(Decimal("0.01"))
                except HTTPException as e:
                    # Release held seats if promotion is invalid
                    await self.trip_seat_repo.bulk_release_hold_seats(
                        trip_id=data.trip_id,
                        travel_date=travel_date,
                        seat_ids=[s.id for s in held_seats],
                        user_id=user_id,
                    )
                    raise e

            net_amount = total_amount - discount_amount

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
                promotion_id=promotion.id if promotion else None,
                total_amount=total_amount,
                service_fee=Decimal("0.0"),
                discount_amount=discount_amount,
                net_amount=net_amount,
                booking_date=datetime.now(timezone.utc),
                expiry_date=self._calculate_expiry(),
                travel_date=travel_date,
                booking_seats=booking_seats_list,
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
                detail=f"Booking creation failed: {str(e)}",
            )

    # ==============================================
    # Booking Price Preview (Summary)
    # ==============================================

    async def preview_booking_price(
        self,
        data: BookingPricePreviewRequest,
        user_id: uuid.UUID,
    ) -> BookingPricePreviewResponse:
        """
        Booking Form မှ Summary ပြရန် Price ကို Backend မှ တွက်ချက်ပေးခြင်း။
        Promo Code ထည့်လိုက်လျှင် Discount နှုတ်ပြီး Final Price ကို Preview ပြပေးမည်။

        Flow:
        1. Trip ရှိမရှိ စစ်ဆေးခြင်း
        2. Selected Seats ရှာဖွေခြင်း (TripSeat IDs သို့မဟုတ် Seat IDs)
        3. Seat တစ်ခုချင်းစီ၏ Price ကို Festive / User Type အလိုက် တွက်ချက်ခြင်း
        4. Subtotal / Service Fee / Total တွက်ချက်ခြင်း
        5. Promo Code ရှိပါက Discount နှုတ်၍ Net Amount ပြခြင်း
        """
        # 1️⃣ Trip ရှိမရှိ စစ်ဆေးခြင်း
        trip = await self.trip_repo.get_by_id(data.trip_id)
        if not trip or not trip.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Trip not found or inactive.",
            )

        # 2️⃣ Selected Seats ရှာဖွေခြင်း
        # ထို travel_date အတွက် TripSeat မရှိသေးပါက Auto-initialize လုပ်ပေးမည်
        await self.trip_seat_service.get_or_create_seats_for_date(
            trip_id=data.trip_id,
            travel_date=data.travel_date,
        )

        # Seat IDs ဖြင့် ဖြစ်စေ၊ TripSeat IDs ဖြင့် ဖြစ်စေ ရှာဖွေနိုင်ရန်
        trip_seats = await self.trip_seat_repo.get_by_trip_or_seat_ids(data.seat_ids)
        if not trip_seats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No valid seats found for the given seat_ids.",
            )

        # Filter only seats that belong to this trip & travel_date
        valid_seats = []
        for ts in trip_seats:
            if ts.trip_id == data.trip_id and ts.travel_date == data.travel_date:
                valid_seats.append(ts)

        if not valid_seats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected seats do not match the trip/travel_date.",
            )

        if len(valid_seats) != len(data.seat_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more selected seats do not belong to this trip/travel_date.",
            )

        # 3️⃣ Seat Price တွက်ချက်ခြင်း
        user_type = (data.user_type or "local").lower()
        subtotal = Decimal("0.0")
        seat_items: List[PricePreviewSeatItem] = []

        for ts in valid_seats:
            price = await self._compute_seat_price(
                trip=trip,
                travel_date=data.travel_date,
                user_type=user_type,
            )
            subtotal += price

            seat_items.append(
                PricePreviewSeatItem(
                    trip_seat_id=ts.id,
                    seat_id=getattr(ts, "seat_id", None),
                    seat_number=ts.seat.seat_number if ts.seat else None,
                    row_number=ts.seat.row_number if ts.seat else None,
                    column_number=ts.seat.column_number if ts.seat else None,
                    position=(
                        ts.seat.position.value if ts.seat and ts.seat.position else None
                    ),
                    price=price,
                )
            )

        subtotal = subtotal.quantize(Decimal("0.01"))
        service_fee = Decimal("0.00")
        total_amount = subtotal + service_fee
        discount_applied = Decimal("0.00")

        # ✅ Promo Code ရှိပါက Discount နှုတ်ခြင်း
        promo_result = None
        if data.promo_code:
            promo_result = await self.promo_service.apply_promotion(
                user_id=user_id,
                data=ApplyPromotionRequest(
                    promo_code=data.promo_code,
                    booking_total=float(total_amount),
                ),
            )
            discount_applied = Decimal(str(promo_result.discount_applied)).quantize(
                Decimal("0.01")
            )

        net_amount = max(total_amount - discount_applied, 0).quantize(Decimal("0.01"))

        return BookingPricePreviewResponse(
            trip_id=data.trip_id,
            travel_date=data.travel_date,
            user_type=user_type,
            seats=seat_items,
            total_seats=len(valid_seats),
            subtotal=subtotal,
            service_fee=service_fee,
            total_amount=total_amount,
            promo_code=data.promo_code if data.promo_code else None,
            promotion_id=promo_result.promotion_id if promo_result else None,
            promotion_name=promo_result.promotion_name if promo_result else None,
            discount_percentage=(
                promo_result.discount_percentage if promo_result else None
            ),
            discount_amount=promo_result.discount_amount if promo_result else None,
            discount_applied=discount_applied,
            net_amount=net_amount,
        )

    async def get_booking_by_id(
        self,
        booking_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
    ) -> BookingResponse:
        """Booking ID ဖြင့် ရှာဖွေခြင်း"""
        booking = await self.repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # Check authorization (user can only view their own bookings unless admin)
        if user_id and booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this booking",
            )

        return await self._to_response(booking)

    async def get_user_bookings(
        self,
        user_id: uuid.UUID,
        status: Optional[BookingStatus] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[BookingResponse]:
        bookings, total = await self.repo.get_by_user_id(
            user_id=user_id, status=status, page=page, size=size
        )
        items = [await self._to_response(b) for b in bookings]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=(total + size - 1) // size if total else 0,
        )

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
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # Check authorization
        if booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to update this booking",
            )

        # Can't update if booking is already confirmed or cancelled
        if booking.status in [
            BookingStatus.CONFIRMED,
            BookingStatus.CANCELLED,
            BookingStatus.REFUNDED,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot update booking with status: {booking.status}",
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
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
            )

        # Check authorization
        if booking.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to cancel this booking",
            )

        # Can only cancel pending bookings
        if booking.status not in [
            BookingStatus.PENDING,
            BookingStatus.AWAITING_PAYMENT,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel booking with status: {booking.status}",
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

        # Cancel promotion usage if exists
        if booking.promotion_usage:
            await self.promo_service.cancel_usage(booking.promotion_usage.id)

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
                status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
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
            # Cancel promotion usage if exists
            if booking.promotion_usage:
                await self.promo_service.cancel_usage(booking.promotion_usage.id)
            expired_count += 1
        await self.db.commit()
        return expired_count
