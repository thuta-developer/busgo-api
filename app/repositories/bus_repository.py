import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.bus import Bus
from app.models.bus_company import BusCompany
from app.schemas.bus import BusCreate, BusUpdate


class BusRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Bus], int]:
        query = select(Bus).options(selectinload(Bus.company))

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    Bus.name.ilike(search_filter),
                    Bus.bus_number.ilike(search_filter),
                )
            )

        if is_active is not None:
            query = query.where(Bus.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * size
        query = query.order_by(Bus.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_by_id(self, id: uuid.UUID) -> Optional[Bus]:
        stmt = (
            select(Bus)
            .options(selectinload(Bus.company))
            .where(Bus.id == id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_bus_number(self, bus_number: str) -> Optional[Bus]:
        """Bus Number တူရှိ/မရှိ စစ်ဆေးခြင်း (Duplicate ကာကွယ်ရန်)"""
        stmt = select(Bus).where(Bus.bus_number == bus_number)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_company_by_id(self, company_id: uuid.UUID) -> Optional[BusCompany]:
        """Company ID ရှိ/မရှိ စစ်ဆေးခြင်း (Foreign Key မှားယွင်းမှု ကာကွယ်ရန်)"""
        stmt = select(BusCompany).where(BusCompany.id == company_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: BusCreate) -> Bus:
        bus = Bus(**data.model_dump())
        self.db.add(bus)
        await self.db.commit()

        # Company relationship ကို Eager Load လုပ်ပြီး ပြန်ယူသည်
        stmt = (
            select(Bus)
            .options(selectinload(Bus.company))
            .where(Bus.id == bus.id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update(self, bus: Bus, data: BusUpdate) -> Bus:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(bus, key, value)
        await self.db.commit()

        # Company relationship ကို Eager Load လုပ်ပြီး ပြန်ယူသည်
        stmt = (
            select(Bus)
            .options(selectinload(Bus.company))
            .where(Bus.id == bus.id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, bus: Bus) -> None:
        await self.db.delete(bus)
        await self.db.commit()