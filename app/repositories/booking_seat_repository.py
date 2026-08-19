import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking_seat import BookingSeat
from app.schemas.booking import BookingSeatCreate


class BookingSeatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: BookingSeatCreate) -> BookingSeat:
        booking_seat = BookingSeat(**data.model_dump())
        self.db.add(booking_seat)
        await self.db.commit()
        await self.db.refresh(booking_seat)
        return booking_seat

    async def bulk_create(self, booking_seats: List[BookingSeat]) -> List[BookingSeat]:
        self.db.add_all(booking_seats)
        await self.db.commit()
        for bs in booking_seats:
            await self.db.refresh(bs)
        return booking_seats

    async def get_by_booking_id(self, booking_id: uuid.UUID) -> List[BookingSeat]:
        stmt = select(BookingSeat).where(BookingSeat.booking_id == booking_id)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())