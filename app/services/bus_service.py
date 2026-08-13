import uuid
import math
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.bus_repository import BusRepository
from app.schemas.bus import BusCreate, BusUpdate, BusResponse
from app.schemas.common import PaginatedResponse


class BusService:
    def __init__(self, db: AsyncSession):
        self.repo = BusRepository(db)

    async def get_all_buses(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[BusResponse]:
        """Search + Filter + Pagination ဖြင့် Bus စာရင်းကို ပြန်ပေးသည်။"""
        buses, total = await self.repo.get_all(
            search=search,
            is_active=is_active,
            page=page,
            size=size,
        )
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [BusResponse.model_validate(b) for b in buses]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    async def get_bus_by_id(self, bus_id: uuid.UUID) -> BusResponse:
        """Bus ID ဖြင့် ရှာဖွေခြင်း (မရှိပါက 404 ပြမည်)"""
        bus = await self.repo.get_by_id(bus_id)
        if not bus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus not found",
            )
        return BusResponse.model_validate(bus)

        
    async def create_bus(self, data: BusCreate) -> BusResponse:
        """Bus အသစ် ထည့်သွင်းခြင်း"""

        # 1. Company ID ရှိ/မရှိ စစ်ဆေးခြင်း (Foreign Key မှားယွင်းမှု ကာကွယ်ရန်)
        company = await self.repo.get_company_by_id(data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bus company not found. Please provide a valid company_id.",
            )

        # 2. Bus Number တူရှိ/မရှိ စစ်ဆေးခြင်း (Duplicate ကာကွယ်ရန်)
        existing = await self.repo.get_by_bus_number(data.bus_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bus with number '{data.bus_number}' already exists",
            )

        bus = await self.repo.create(data)
        return BusResponse.model_validate(bus)

    async def update_bus(
        self, bus_id: uuid.UUID, data: BusUpdate
    ) -> BusResponse:
        """Bus အချက်အလက် ပြင်ဆင်ခြင်း"""
        bus = await self.repo.get_by_id(bus_id)
        if not bus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus not found",
            )

        # Company ID ပြောင်းလဲတော့မည်ဆိုလျှင် ရှိ/မရှိ စစ်ဆေးသည်
        if data.company_id is not None and data.company_id != bus.company_id:
            company = await self.repo.get_company_by_id(data.company_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Bus company not found. Please provide a valid company_id.",
                )

        # Bus Number ပြောင်းလဲတော့မည်ဆိုလျှင် တူရှိ/မရှိ စစ်ဆေးသည်
        if data.bus_number is not None and data.bus_number != bus.bus_number:
            existing = await self.repo.get_by_bus_number(data.bus_number)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bus with number '{data.bus_number}' already exists",
                )

        updated = await self.repo.update(bus, data)
        return BusResponse.model_validate(updated)

    async def delete_bus(self, bus_id: uuid.UUID) -> dict:
        """Bus ဖျက်ထုတ်ခြင်း"""
        bus = await self.repo.get_by_id(bus_id)
        if not bus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus not found",
            )
        await self.repo.delete(bus)
        return {"message": "Bus deleted successfully"}