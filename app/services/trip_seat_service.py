import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime,time, timezone
from decimal import Decimal

from app.models.trip_seat import TripSeat, TripSeatStatus
from app.models.seat import Seat
from app.repositories.trip_seat_repository import TripSeatRepository
from app.repositories.trip_repository import TripRepository
from app.repositories.seat_repository import SeatRepository
from app.schemas.trip_seat import (
    TripSeatCreate,
    TripSeatUpdate,
    TripSeatResponse,
    TripSeatBulkResponse,
    BulkHoldRequest,
    BulkBookRequest,
    BulkConfirmRequest,
    BulkReleaseRequest,
)


class TripSeatService:
    def __init__(self, db: AsyncSession):
        self.repo = TripSeatRepository(db)
        self.seat_repo = SeatRepository(db)
        self.trip_repo = TripRepository(db)

    async def _to_response(
        self, trip_seat: TripSeat, user_type: Optional[str] = "local"
    ) -> TripSeatResponse:
        res = TripSeatResponse.model_validate(trip_seat)
        user_type = (user_type or "local").lower()

        trip = getattr(trip_seat, "trip", None)
        if trip:
            # ၁။ travel_date နှင့် festival date များကို timezone-aware ဖြစ်အောင် ပြင်ဆင်ပါ
            check_date = trip_seat.travel_date
            if isinstance(check_date, date) and not isinstance(check_date, datetime):
                check_date = datetime.combine(check_date, time.min, tzinfo=timezone.utc)

            festival_start = trip.festival_start_date
            festival_end = trip.festival_end_date

            is_festival = False
            if festival_start and festival_end:
                if festival_start.tzinfo is None:
                    festival_start = festival_start.replace(tzinfo=timezone.utc)
                if festival_end.tzinfo is None:
                    festival_end = festival_end.replace(tzinfo=timezone.utc)

                # travel_date သည် festival ရဲ့ စမည့်ရက် နှင့် ဆုံးမည့်ရက် ကြားထဲ ရှိမရှိ စစ်ပါ
                if festival_start <= check_date <= festival_end:
                    is_festival = True

            # ၂။ Price Field Name များကို Trip Model အတိုင်း မှန်ကန်စွာ Mapping လုပ်ပါ
            regular_base_price = (
                trip.foreigner_price if user_type == "foreigner" else trip.local_price
            )
            festival_base_price = (
                trip.foreigner_festival_price
                if user_type == "foreigner"
                else trip.local_festival_price
            )

            # ၃။ Festival ရက် ဖြစ်ပါက festival_price ကို ယူမည်
            if is_festival and festival_base_price is not None:
                res.price = festival_base_price
            else:
                res.price = regular_base_price or Decimal("0.0")
        else:
            res.price = Decimal("0.0")

        if trip_seat.seat:
            res.seat_number = trip_seat.seat.seat_number
            res.row_number = trip_seat.seat.row_number
            res.column_number = trip_seat.seat.column_number
            res.position = (
                trip_seat.seat.position.value if trip_seat.seat.position else None
            )
        return res

    async def _to_bulk_response(
        self, trip_id: uuid.UUID, travel_date: date, trip_seats: List[TripSeat]
    ) -> TripSeatBulkResponse:
        """Convert a list of TripSeats to a bulk response with trip_id and travel_date."""
        return TripSeatBulkResponse(
            trip_id=trip_id,
            travel_date=travel_date,
            seats=[await self._to_response(ts) for ts in trip_seats],
        )

    async def get_or_create_seats_for_date(
        self, trip_id: uuid.UUID, travel_date: date
    ) -> List[TripSeat]:
        """
        ထို trip_id + travel_date အတွက် ခုံ Record များ မရှိသေးပါက
        Bus ၏ Seat Structure အတိုင်း Auto-generate (Lazy Initialize) လုပ်ပေးမည်။
        """
        # ၁။ Trip ရှိမရှိ စစ်ဆေးမည်
        trip = await self.trip_repo.get_by_id(trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found.",
            )

        # ၂။ ထိုရက်အတွက် TripSeat ရှိပြီးသားလား စစ်ဆေးမည်
        existing = await self.repo.get_all_for_trip_and_date(trip_id, travel_date)
        if existing:
            return existing

        # ၃။ မရှိသေးပါက Bus တွင် သတ်မှတ်ထားသော ထိုင်ခုံများအား ရယူမည်
        seats = await self.seat_repo.get_seats_by_bus_id(trip.bus_id)
        if not seats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus has no seats defined.",
            )

        # ၄။ TripSeat Record အသစ်များ တည်ဆောက်မည်
        new_trip_seats = [
            TripSeat(
                trip_id=trip_id,
                seat_id=seat.id,
                travel_date=travel_date,
                status=TripSeatStatus.AVAILABLE,
            )
            for seat in seats
        ]

        return await self.repo.bulk_create(new_trip_seats)

    async def initialize_trip_seats(
        self, trip_id: uuid.UUID, bus_id: uuid.UUID, travel_date: date
    ) -> List[TripSeatResponse]:
        """
        Trip တစ်ခု ဖန်တီးပြီးတာနဲ့ ဒီ bus ရဲ့ seat အားလုံးအတွက် TripSeat records ကို auto-generate လုပ်ပေးတယ်။
        """
        seats = await self.seat_repo.get_seats_by_bus_id(bus_id)
        if not seats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus has no seats defined.",
            )

        existing = await self.repo.get_all_for_trip_and_date(trip_id, travel_date)
        if existing:
            return [await self._to_response(ts) for ts in existing]

        trip_seats = []
        for seat in seats:
            ts = TripSeat(
                trip_id=trip_id, seat_id=seat.id, status=TripSeatStatus.AVAILABLE,
            )
            trip_seats.append(ts)

        created = await self.repo.bulk_create(trip_seats)
        return [await self._to_response(ts) for ts in created]

    

    # ========== Get seats for a trip ==========
    async def get_trip_seats(
        self,
        trip_id: uuid.UUID,
        travel_date: date,
        status_filter: Optional[TripSeatStatus] = None,
        user_type: Optional[str] = "local",
    ) -> List[TripSeatResponse]:
        """သတ်မှတ်ထားသော ရက်စွဲအလိုက် Trip ၏ ထိုင်ခုံများအားလုံးကို ရယူမည်။"""
        # Auto-initialize check
        trip_seats = await self.get_or_create_seats_for_date(trip_id, travel_date)

        if status_filter:
            trip_seats = [ts for ts in trip_seats if ts.status == status_filter]

        return [await self._to_response(ts, user_type=user_type) for ts in trip_seats]

    # ========== Bulk operations ==========

    async def bulk_hold_seats(
        self, trip_id: uuid.UUID, payload: BulkHoldRequest, user_id: uuid.UUID
    ) -> TripSeatBulkResponse:
        """ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် Hold လုပ်ခြင်း"""

        await self.get_or_create_seats_for_date(trip_id, payload.travel_date)

        held = await self.repo.bulk_hold_seats(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            seat_ids=payload.seat_ids,
            user_id=user_id,
        )
        if not held:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No seats could be held. They might be already held or booked.",
            )
        return await self._to_bulk_response(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            trip_seats=held,
        )

    async def bulk_book_seats(
        self, trip_id: uuid.UUID, payload: BulkBookRequest, user_id: uuid.UUID
    ) -> TripSeatBulkResponse:
        """ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် Direct Book လုပ်ခြင်း။"""
        await self.get_or_create_seats_for_date(trip_id, payload.travel_date)

        booked = await self.repo.bulk_book_seats(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            seat_ids=payload.seat_ids,
            user_id=user_id,
        )
        if not booked:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No seats could be booked. They might be unavailable or already booked.",
            )
        return await self._to_bulk_response(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            trip_seats=booked,
        )

    async def bulk_confirm_booking(
        self, trip_id: uuid.UUID, payload: BulkConfirmRequest, user_id: uuid.UUID
    ) -> TripSeatBulkResponse:
        """Hold ထားသော ထိုင်ခုံများကို တစ်ပြိုင်နက် အပြီးအပိုင် Confirm (BOOKED) ပြုလုပ်ခြင်း။"""
        confirmed = await self.repo.bulk_confirm_booking(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            seat_ids=payload.seat_ids,
            user_id=user_id,
        )
        if not confirmed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot confirm bookings. Holds might have expired or you are not the holder.",
            )
        return await self._to_bulk_response(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            trip_seats=confirmed,
        )

    async def bulk_release_hold(
        self, trip_id: uuid.UUID, payload: BulkReleaseRequest, user_id: uuid.UUID
    ) -> TripSeatBulkResponse:
        """Hold ထားသော ထိုင်ခုံများကို တစ်ပြိုင်နက် ပြန်လွှတ် (Release) ပြုလုပ်ခြင်း။"""
        released = await self.repo.bulk_release_hold_seats(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            seat_ids=payload.seat_ids,
            user_id=user_id,
        )
        if not released:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No held seats found or you are not the holder.",
            )
        return await self._to_bulk_response(
            trip_id=trip_id,
            travel_date=payload.travel_date,
            trip_seats=released,
        )
