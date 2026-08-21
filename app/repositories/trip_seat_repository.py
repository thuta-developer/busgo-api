import uuid
from typing import List, Optional
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime, time, timezone, timedelta, date

from app.models.trip_seat import TripSeat, TripSeatStatus
from app.models.trip import Trip
from app.models.seat import Seat


class TripSeatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _base_options(self):
        """Common eager-load options: Seat, Trip and Trip.bus."""
        return (
            selectinload(TripSeat.seat),
            selectinload(TripSeat.trip).selectinload(Trip.bus),
        )

    async def _get_many_with_seat(
        self, trip_seat_ids: List[uuid.UUID]
    ) -> List[TripSeat]:
        """Fetch multiple TripSeats with their Seat, Trip and Trip.bus relationships eagerly loaded."""
        if not trip_seat_ids:
            return []
        stmt = (
            select(TripSeat)
            .where(TripSeat.id.in_(trip_seat_ids))
            .options(*self._base_options())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_all_for_trip_and_date(
        self,
        trip_id: uuid.UUID,
        travel_date: date,
        status: Optional[TripSeatStatus] = None,
    ) -> List[TripSeat]:
        """Trip ID နှင့် Travel Date အလိုက် ထိုင်ခုံများအားလုံးကို ရှာဖွေခြင်း။"""
        stmt = (
            select(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    TripSeat.travel_date == travel_date,
                )
            )
            .options(*self._base_options())
        )
        if status:
            stmt = stmt.where(TripSeat.status == status)
        stmt = stmt.order_by(TripSeat.seat_id.asc())  # or by seat_number
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_ids(self, trip_seat_ids: List[uuid.UUID]) -> List[TripSeat]:
        """TripSeat ID များဖြင့် ရှာဖွေခြင်း (Seat, Trip & Trip.bus relationships ပါ)"""
        if not trip_seat_ids:
            return []
        stmt = (
            select(TripSeat)
            .where(TripSeat.id.in_(trip_seat_ids))
            .options(*self._base_options())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_trip_or_seat_ids(
        self, seat_ids: List[uuid.UUID]
    ) -> List[TripSeat]:
        """Fetch TripSeats when callers provide TripSeat IDs or Seat IDs."""
        if not seat_ids:
            return []
        stmt = (
            select(TripSeat)
            .where(
                or_(
                    TripSeat.id.in_(seat_ids),
                    TripSeat.seat_id.in_(seat_ids),
                )
            )
            .options(*self._base_options())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def bulk_create(self, trip_seats: List[TripSeat]) -> List[TripSeat]:
        """TripSeat အသစ်များကို Bulk Create လုပ်ပြီး Seat Relationship ဖြင့် ပြန်လည်ပေးပို့ခြင်း။"""
        self.db.add_all(trip_seats)
        await self.db.commit()
        ids = [ts.id for ts in trip_seats]
        return await self._get_many_with_seat(ids)

    async def bulk_hold_seats(
        self,
        trip_id: uuid.UUID,
        travel_date: date,
        seat_ids: List[uuid.UUID],
        user_id: uuid.UUID,
        hold_duration_seconds: int = 600,
    ) -> List[TripSeat]:
        """
        ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် AVAILABLE မှ HELD သို့ပြောင်းသည်။
        seat_ids တစ်ခုချင်းစီသည် TripSeat.id သို့မဟုတ် Seat.id ဖြစ်နိုင်သည်။
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=hold_duration_seconds)

        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    TripSeat.travel_date == travel_date,
                    or_(
                        TripSeat.id.in_(seat_ids),
                        TripSeat.seat_id.in_(seat_ids),
                    ),
                    or_(
                        # ၁။ ခုံ လွတ်နေလျှင် Hold ရမည်
                        TripSeat.status == TripSeatStatus.AVAILABLE,
                        # ၂။ မိမိကိုယ်တိုင် Hold ထားပြီး သက်တမ်းမကုန်သေးလျှင် Renew လုပ်ခွင့်ရှိမည်
                        and_(
                            TripSeat.status == TripSeatStatus.HELD,
                            TripSeat.booked_by == user_id,
                            TripSeat.hold_expires_at > now,
                        ),
                        # ၃။ သူများ Hold ထားသော်လည်း သက်တမ်းကုန်သွားပါက Hold လို့ရမည်
                        and_(
                            TripSeat.status == TripSeatStatus.HELD,
                            TripSeat.hold_expires_at <= now,
                        ),
                    ),
                )
            )
            .values(
                status=TripSeatStatus.HELD,
                booked_by=user_id,
                booked_at=None,
                hold_expires_at=expires_at,
            )
            .returning(TripSeat.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        updated_ids = list(result.scalars().all())
        return await self._get_many_with_seat(updated_ids)

    async def bulk_book_seats(
        self,
        trip_id: uuid.UUID,
        travel_date: date,
        seat_ids: List[uuid.UUID],
        user_id: uuid.UUID,
    ) -> List[TripSeat]:
        """
        ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် AVAILABLE မှ BOOKED သို့ပြောင်းသည်။
        """
        now = datetime.now(timezone.utc)

        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    TripSeat.travel_date == travel_date,
                    or_(
                        TripSeat.id.in_(seat_ids),
                        TripSeat.seat_id.in_(seat_ids),
                    ),
                    TripSeat.status == TripSeatStatus.AVAILABLE,
                )
            )
            .values(
                status=TripSeatStatus.BOOKED,
                booked_by=user_id,
                booked_at=now,
            )
            .returning(TripSeat.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        updated_ids = list(result.scalars().all())
        return await self._get_many_with_seat(updated_ids)

    async def bulk_confirm_booking(
        self,
        trip_id: uuid.UUID,
        travel_date: date,
        seat_ids: List[uuid.UUID],
        user_id: uuid.UUID,
    ) -> List[TripSeat]:
        """
        HELD ထားသော ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် BOOKED အဖြစ်အတည်ပြုသည်။
        (Hold ချိန်မကုန်သေးဘဲ ထို User ကိုင်ထားမှသာ ရမည်)
        """
        now = datetime.now(timezone.utc)

        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    TripSeat.travel_date == travel_date,
                    or_(
                        TripSeat.id.in_(seat_ids),
                        TripSeat.seat_id.in_(seat_ids),
                    ),
                    TripSeat.status == TripSeatStatus.HELD,
                    TripSeat.booked_by == user_id,
                    TripSeat.hold_expires_at > now,
                )
            )
            .values(
                status=TripSeatStatus.BOOKED,
                booked_at=now,
                hold_expires_at=None,
            )
            .returning(TripSeat.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        updated_ids = list(result.scalars().all())
        return await self._get_many_with_seat(updated_ids)

    async def bulk_release_hold_seats(
        self,
        trip_id: uuid.UUID,
        travel_date: date,
        seat_ids: List[uuid.UUID],
        user_id: uuid.UUID,
    ) -> List[TripSeat]:
        """
        HELD ထားသော ထိုင်ခုံများစွာကို တစ်ပြိုင်နက် AVAILABLE သို့ပြန်လွှတ်သည်။
        """
        stmt = (
            update(TripSeat)
            .where(
                and_(
                    TripSeat.trip_id == trip_id,
                    TripSeat.travel_date == travel_date,
                    or_(
                        TripSeat.id.in_(seat_ids),
                        TripSeat.seat_id.in_(seat_ids),
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
            .returning(TripSeat.id)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()
        updated_ids = list(result.scalars().all())
        return await self._get_many_with_seat(updated_ids)

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
