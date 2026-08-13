import uuid
from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bus_company import BusCompany
from app.schemas.bus_company import BusCompanyCreate, BusCompanyUpdate

class BusCompanyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[BusCompany], int]:
        """Search + Filter + Pagination ဖြင့် Company များကို ရယူသည်။"""
        query = select(BusCompany)

        # Search: name / email / contact_phone / address တွင် ရှာဖွေခြင်း
        if search:
            search_filter = f"%{search}%"
            query = query.where(
                or_(
                    BusCompany.name.ilike(search_filter),
                    BusCompany.email.ilike(search_filter),
                    BusCompany.contact_phone.ilike(search_filter),
                    BusCompany.address.ilike(search_filter),
                )
            )

        # Filter: active company များသာ ရှာဖွေခြင်း
        if is_active is not None:
            query = query.where(BusCompany.is_active == is_active)

        # Total ရေတွက်ခြင်း
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Pagination: offset = (page - 1) * size
        offset = (page - 1) * size
        query = query.order_by(BusCompany.created_at.desc()).offset(offset).limit(size)

        result = await self.db.execute(query)
        companies = list(result.scalars().all())

        return companies, total

    async def get_by_id(self, id: uuid.UUID) -> Optional[BusCompany]:
        stmt = select(BusCompany).where(BusCompany.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Optional[BusCompany]:
        """Company အမည်တူ ရှိ/မရှိ စစ်ဆေးခြင်း (Duplicate ကာကွယ်ရန်)"""
        stmt = select(BusCompany).where(BusCompany.name == name)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, data: BusCompanyCreate) -> BusCompany:
        company = BusCompany(**data.model_dump())
        self.db.add(company)
        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def update(self, company: BusCompany, data: BusCompanyUpdate) -> BusCompany:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(company, key, value)
        await self.db.commit()
        await self.db.refresh(company)
        return company

    async def delete(self, company: BusCompany) -> None:
        await self.db.delete(company)
        await self.db.commit()