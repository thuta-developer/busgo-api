import uuid
from typing import List, Optional
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, time, timezone, timedelta

from app.models.trip_seat import TripSeat, TripSeatStatus
from app.models.seat import Seat
from app.schemas.trip_seat import TripSeatCreate, TripSeatUpdate


class TripSeatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, trip_seat_id: uuid.UUID) -> Optional[TripSeat]:
        stmt = select(TripSeat).where(TripSeat.id == trip_seat_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_with_seat(self, trip_seat_id: uuid.UUID) -> Optional[TripSeat]:
        """Fetch a TripSeat with its Seat relationship eagerly loaded."""
        stmt = (
            select(TripSeat)
            .where(TripSeat.id == trip_seat_id)
            .options(selectinload(TripSeat.seat))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_trip_and_seat(self, trip_id: uuid.UUID, seat_id: uuid.UUID) -> Optional[TripSeat]:
        stmt = select(TripSeat).where(
            and_(TripSeat.trip_id == trip_id, TripSeat.seat_id == seat_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_for_trip(
        self, trip_id: uuid.UUID, status: Optional[TripSeatStatus] = None
    ) -> List[TripSeat]:
        stmt = (
            select(TripSeat)
            .where(TripSeat.trip_id == trip_id)
            .options(selectinload(TripSeat.seat))
        )
        if status:
            stmt = stmt.where(TripSeat.status == status)
        stmt = stmt.order_by(TripSeat.seat_id.asc())  # or by seat_number
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: TripSeatCreate) -> TripSeat:
        trip_seat = TripSeat(**data.model_dump())
        self.db.add(trip_seat)
        await self.db.commit()
        return await self._get_with_seat(trip_seat.id)


    async def bulk_create(self, trip_seats: List[TripSeat]) -> List[TripSeat]:
        self.db.add_all(trip_seats)
        await self.db.commit()
        # Re-fetch with seat relationship eagerly loaded to avoid MissingGreenlet
        # when accessing trip_seat.seat in async context.
        ids = [ts.id for ts in trip_seats]
        stmt = (
            select(TripSeat)
            .where(TripSeat.id.in_(ids))
            .options(selectinload(TripSeat.seat))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update(self, trip_seat: TripSeat, data: TripSeatUpdate) -> TripSeat:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(trip_seat, key, value)
        await self.db.commit()
        return await self._get_with_seat(trip_seat.id)

    async def delete(self, trip_seat: TripSeat) -> None:
        await self.db.delete(trip_seat)
        await self.db.commit()


    async def book_seat(self, trip_id: uuid.UUID, seat_id: uuid.UUID, user_id: uuid.UUID) -> Optional[TripSeat]:
        # Using optimistic lock or SELECT FOR UPDATE? For simplicity, we use a query to update only if AVAILABLE
        # seat_id can be either the TripSeat.id or the Seat.id
        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    or_(
                        TripSeat.id == seat_id,
                        TripSeat.seat_id == seat_id,
                    ),
                    TripSeat.status == TripSeatStatus.AVAILABLE,
                )
            )
            .values(
                status=TripSeatStatus.BOOKED,
                booked_by=user_id,
                booked_at=datetime.now(timezone.utc),
            )
            .returning(TripSeat)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        row = result.scalar_one_or_none()
        if row:
            return await self._get_with_seat(row.id)
        return None

    async def hold_seat(
        self, 
        trip_id: uuid.UUID, 
        seat_id: uuid.UUID, 
        user_id: uuid.UUID, 
        hold_duration_seconds: int = 300
    ) -> Optional[TripSeat]:
        """
        ထိုင်ခုံကို AVAILABLE မှ HELD သို့ပြောင်းပြီး သတ်မှတ်ချိန်အထိ သိမ်းဆည်းပေးသည်။
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=hold_duration_seconds)

        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    or_(
                        TripSeat.id == seat_id,
                        TripSeat.seat_id == seat_id,
                    ),
                    TripSeat.status == TripSeatStatus.AVAILABLE,
                )
            )
            .values(
                status=TripSeatStatus.HELD,
                booked_by=user_id,
                booked_at=None,
                hold_expires_at=expires_at,
            )
            .returning(TripSeat)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        row = result.scalar_one_or_none()
        if row:
            return await self._get_with_seat(row.id)
        return None

    async def confirm_booking(
        self, 
        trip_id: uuid.UUID, 
        seat_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[TripSeat]:
        """
        HELD ထားသော ထိုင်ခုံကို အပြီးအပိုင် BOOKED အဖြစ်အတည်ပြုသည်။
        (Hold ချိန်မကုန်သေးဘဲ ထို User ကိုင်ထားမှသာ ရမည်)
        """
        now = datetime.now(timezone.utc)

        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    or_(
                        TripSeat.id == seat_id,
                        TripSeat.seat_id == seat_id,
                    ),
                    TripSeat.status == TripSeatStatus.HELD,
                    TripSeat.booked_by == user_id,
                    TripSeat.hold_expires_at > now,  # သက်တမ်းမကုန်သေးပါ
                )
            )
            .values(
                status=TripSeatStatus.BOOKED,
                booked_at=now,
                hold_expires_at=None,  # သက်တမ်းကို ရှင်းပစ်သည်
            )
            .returning(TripSeat)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        row = result.scalar_one_or_none()
        if row:
            return await self._get_with_seat(row.id)
        return None

    async def release_hold_seat(
        self, 
        trip_id: uuid.UUID, 
        seat_id: uuid.UUID, 
        user_id: uuid.UUID
    ) -> Optional[TripSeat]:
        """
        Hold ထားသော ထိုင်ခုံကို ပြန်လွှတ်ပေးခြင်း (User က ကိုယ်တိုင်ပယ်ဖျက်ခြင်း သို့မဟုတ် ငွေမသွင်းလို့)
        """
        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    or_(
                        TripSeat.id == seat_id,
                        TripSeat.seat_id == seat_id,
                    ),
                    TripSeat.status == TripSeatStatus.HELD,
                    TripSeat.booked_by == user_id,
                )
            )
            .values(
                status=TripSeatStatus.AVAILABLE,
                hold_expires_at=None,
                booked_by=None,
            )
            .returning(TripSeat)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        row = result.scalar_one_or_none()
        if row:
            return await self._get_with_seat(row.id)
        return None

    async def release_expired_holds(self) -> int:
        """
        သက်တမ်းကုန်သွားသော HELD များကို AVAILABLE ပြန်ပြောင်းပေးသည်။
        (Cron job သို့မဟုတ် Background task ဖြင့် ခေါ်သုံးရန်)
        """
        now = datetime.now(timezone.utc)
        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.status == TripSeatStatus.HELD,
                    TripSeat.hold_expires_at <= now,
                )
            )
            .values(
                status=TripSeatStatus.AVAILABLE,
                booked_by=None,
                hold_expires_at=None,
            )
            .returning(TripSeat.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        released_count = len(result.scalars().all())
        return released_count




        
