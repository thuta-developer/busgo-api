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
        
        # 1. Filter conditions များကို စုစည်းခြင်း
        filters = []

        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    BusCompany.name.ilike(search_filter),
                    BusCompany.email.ilike(search_filter),
                    BusCompany.contact_phone.ilike(search_filter),
                    BusCompany.address.ilike(search_filter),
                )
            )

        if is_active is not None:
            filters.append(BusCompany.is_active == is_active)

        # 2. Total Count ရေတွက်ခြင်း (BusCompany.id ကို တိုက်ရိုက် count လုပ်သည်)
        count_stmt = select(func.count(BusCompany.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
            
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar_one() or 0

        # 3. Main Data Query ထုတ်ယူခြင်း
        stmt = select(BusCompany)
        if filters:
            stmt = stmt.where(*filters)

        # 4. Pagination နှင့် Sorting ထည့်သွင်းခြင်း
        offset = (page - 1) * size
        stmt = stmt.order_by(BusCompany.created_at.desc()).offset(offset).limit(size)

        # 5. Result ရယူပြီး Return ပြန်ခြင်း
        result = await self.db.execute(stmt)
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

    async def soft_delete(self, id: uuid.UUID) -> bool:
        company = await self.get_by_id(id)
        if not company:
            return False
        
        company.is_active = False
        await self.db.commit()
        return True