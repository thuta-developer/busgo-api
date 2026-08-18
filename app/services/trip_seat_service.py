import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trip_seat import TripSeat, TripSeatStatus
from app.models.seat import Seat
from app.repositories.trip_seat_repository import TripSeatRepository
from app.repositories.seat_repository import SeatRepository
from app.schemas.trip_seat import TripSeatCreate, TripSeatUpdate, TripSeatResponse, TripSeatBulkResponse


class TripSeatService:
    def __init__(self, db: AsyncSession):
        self.repo = TripSeatRepository(db)
        self.seat_repo = SeatRepository(db)

    async def _to_response(self, trip_seat: TripSeat) -> TripSeatResponse:
        res = TripSeatResponse.model_validate(trip_seat)
        if trip_seat.seat:
            res.seat_number = trip_seat.seat.seat_number
            res.row_number = trip_seat.seat.row_number
            res.column_number = trip_seat.seat.column_number
            res.position = trip_seat.seat.position.value if trip_seat.seat.position else None
        return res

    async def initialize_trip_seats(self, trip_id: uuid.UUID, bus_id: uuid.UUID) -> List[TripSeatResponse]:
        """
        Trip တစ်ခု ဖန်တီးပြီးတာနဲ့ ဒီ bus ရဲ့ seat အားလုံးအတွက် TripSeat records ကို auto-generate လုပ်ပေးတယ်။
        """
        seats = await self.seat_repo.get_seats_by_bus_id(bus_id)
        if not seats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus has no seats defined.",
            )

        existing = await self.repo.get_all_for_trip(trip_id)
        if existing:
            return [await self._to_response(ts) for ts in existing]

        trip_seats = []
        for seat in seats:
            ts = TripSeat(
                trip_id=trip_id,
                seat_id=seat.id,
                status=TripSeatStatus.AVAILABLE
            )
            trip_seats.append(ts)

        created = await self.repo.bulk_create(trip_seats)
        return [await self._to_response(ts) for ts in created]

    # ========== Get seats for a trip ==========
    async def get_trip_seats(
        self, trip_id: uuid.UUID, status: Optional[TripSeatStatus] = None
    ) -> List[TripSeatResponse]:
        trip_seats = await self.repo.get_all_for_trip(trip_id, status)
        return [await self._to_response(ts) for ts in trip_seats]

    # ========== Book a seat ==========
    async def book_seat(
        self, trip_id: uuid.UUID, seat_id: uuid.UUID, user_id: uuid.UUID
    ) -> TripSeatResponse:
        # First check if trip exists? Not needed if repo handles
        updated = await self.repo.book_seat(trip_id, seat_id, user_id)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Seat is not available or already booked.",
            )
        return await self._to_response(updated)

     # ========== Cancel booking ==========
    async def cancel_booking(self, trip_seat_id: uuid.UUID, user_id: uuid.UUID) -> TripSeatResponse:
        ts = await self.repo.get_by_id(trip_seat_id)
        if not ts:
            raise HTTPException(status_code=404, detail="Trip seat not found.")
        if ts.status != TripSeatStatus.BOOKED:
            raise HTTPException(status_code=400, detail="Seat is not booked.")
        if ts.booked_by != user_id:
            # You may allow admin to cancel, but here we check ownership
            raise HTTPException(status_code=403, detail="Not authorized to cancel this booking.")

        update_data = TripSeatUpdate(
            status=TripSeatStatus.AVAILABLE,
            booked_by=None,
            booked_at=None,
        )
        updated = await self.repo.update(ts, update_data)
        return await self._to_response(updated)


    async def hold_seat(self, trip_id: uuid.UUID, seat_id: uuid.UUID, user_id: uuid.UUID) -> TripSeatResponse:
        """Seat ကို Hold လုပ်ခြင်း"""
        hold = await self.repo.hold_seat(trip_id, seat_id, user_id)
        if not hold:
            raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Seat is not available for holding. It might be already held or booked."
                )
                
        return await self._to_response(hold)

    async def confirm_booking(self, trip_id: uuid.UUID, seat_id: uuid.UUID, user_id: uuid.UUID) -> TripSeatResponse:
        """Hold ထားတာကို အပြီးအပိုင် ကြိုတင်မှာယူခြင်း (ငွေပေးချေပြီးချိန်)"""
        confirmed = await self.repo.confirm_booking(trip_id, seat_id, user_id)
        if not confirmed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot confirm booking. Hold might have expired or you are not the holder."
            )
        return await self._to_response(confirmed)

    async def release_hold(self, trip_id: uuid.UUID, seat_id: uuid.UUID, user_id: uuid.UUID) -> dict:
        """Hold ကို ပြန်လွှတ်ခြင်း (ဥပမာ - Payment ပယ်ဖျက်လိုက်ချိန်)"""
        released = await self.repo.release_hold_seat(trip_id, seat_id, user_id)
        if not released:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Held seat not found or you are not the holder."
            )
        return {"message": "Hold released successfully", "seat_id": str(seat_id)}
