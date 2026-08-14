import uuid
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bus import Bus
from app.models.seat import Seat


class SeatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_bus_by_id(self, bus_id: uuid.UUID) -> Optional[Bus]:
        """Bus ID ဖြင့် Bus ရှိမရှိ စစ်ဆေးခြင်း"""
        stmt = select(Bus).where(Bus.id == bus_id)
        result = await self.db.execute(stmt)

        return result.scalar_one_or_none()

    async def delete_seats_by_bus_id(self, bus_id: uuid.UUID) -> None:
        """Bus ID တွင် ရှိသော Seat ဟောင်းများကို ဖျက်ခြင်း"""
        stmt = delete(Seat).where(Seat.bus_id == bus_id)
        await self.db.execute(stmt)

    async def create_seats(self, seats: List[Seat]) -> List[Seat]:
        """Seat အသစ်များကို အများအပြား သိမ်းဆည်းခြင်း"""
        self.db.add_all(seats)
        await self.db.commit()
        return seats

    async def update_bus_total_seats(self, bus: Bus, total_seats: int) -> None:
        """Bus model ရှိ total_seats စာရင်းကို Update လုပ်ခြင်း"""
        bus.total_seats = total_seats
        await self.db.commit()

    async def get_seats_by_bus_id(self, bus_id: uuid.UUID) -> List[Seat]:
        """Bus တစ်ခု၏ Seat များအားလုံးကို Row နှင့် Column အစဉ်လိုက် ပြန်ထုတ်ယူခြင်း"""
        stmt = (
            select(Seat)
            .where(Seat.bus_id == bus_id)
            .order_by(Seat.row_number.asc(), Seat.column_number.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

