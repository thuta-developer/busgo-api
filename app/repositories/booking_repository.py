import uuid
from typing import Optional, List, Tuple
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking, BookingStatus
from app.models.booking_seat import BookingSeat
from app.schemas.booking import BookingCreate, BookingUpdate


class BookingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, booking: Booking) -> Booking:
        self.db.add(booking)
        await self.db.commit()
        # Re-fetch with relationships eagerly loaded to avoid MissingGreenlet
        return await self.get_by_id(booking.id)

    async def get_by_id(self, booking_id: uuid.UUID) -> Optional[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.id == booking_id)
            .options(
                selectinload(Booking.booking_seats),
                selectinload(Booking.user),
                selectinload(Booking.trip),
                selectinload(Booking.payments),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, booking_code: str) -> Optional[Booking]:
        stmt = (
            select(Booking)
            .where(Booking.booking_code == booking_code)
            .options(
                selectinload(Booking.booking_seats),
                selectinload(Booking.user),
                selectinload(Booking.trip),
                selectinload(Booking.payments),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self,
        user_id: uuid.UUID,
        status: Optional[BookingStatus] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Booking], int]:
        """User ID ဖြင့် Booking စာရင်းရှာဖွေခြင်း (Paginated)"""
        query = select(Booking).where(Booking.user_id == user_id)
        
        if status:
            query = query.where(Booking.status == status)
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        # Get items with relationships
        query = (
            query
            .options(
                selectinload(Booking.booking_seats),
                selectinload(Booking.trip),
                selectinload(Booking.payments),
            )
            .order_by(desc(Booking.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_trip_id(
        self,
        trip_id: uuid.UUID,
        status: Optional[BookingStatus] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Booking], int]:
        """Trip ID ဖြင့် Booking စာရင်းရှာဖွေခြင်း"""
        query = select(Booking).where(Booking.trip_id == trip_id)
        
        if status:
            query = query.where(Booking.status == status)
        
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()
        
        query = (
            query
            .options(
                selectinload(Booking.booking_seats),
                selectinload(Booking.payments),
            )
            .order_by(desc(Booking.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update(self, booking: Booking, data: BookingUpdate) -> Booking:
        """Booking အချက်အလက် ပြင်ဆင်ခြင်း"""
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(booking, key, value)
        await self.db.commit()
        # Re-fetch with relationships eagerly loaded to avoid MissingGreenlet
        return await self.get_by_id(booking.id)

    async def update_status(
        self,
        booking_id: uuid.UUID,
        status: BookingStatus,
    ) -> Optional[Booking]:
        """Booking Status ကို Update လုပ်ခြင်း"""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return None
        booking.status = status
        await self.db.commit()
        # Re-fetch with relationships eagerly loaded to avoid MissingGreenlet
        return await self.get_by_id(booking_id)

    async def delete(self, booking_id: uuid.UUID) -> bool:
        """Booking ကို ဖျက်ခြင်း (သို့မဟုတ် Soft Delete)"""
        booking = await self.get_by_id(booking_id)
        if not booking:
            return False
        await self.db.delete(booking)
        await self.db.commit()
        return True

    async def get_expired_bookings(self) -> List[Booking]:
        """သက်တမ်းကုန်သွားသော PENDING Bookings များကို ရှာဖွေခြင်း"""
        now = datetime.now()
        stmt = (
            select(Booking)
            .where(
                and_(
                    Booking.status == BookingStatus.PENDING,
                    Booking.expiry_date < now,
                )
            )
            .options(selectinload(Booking.booking_seats))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    