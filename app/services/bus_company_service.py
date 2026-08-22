import uuid
import math
from typing import Optional
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.bus_company_repository import BusCompanyRepository
from app.schemas.bus_company import (
    BusCompanyCreate,
    BusCompanyUpdate,
    BusCompanyResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.upload_service import (
    upload_to_cloudinary,
    delete_from_cloudinary,
    extract_public_id_from_url,
)


class BusCompanyService:
    def __init__(self, db: AsyncSession):
        self.repo = BusCompanyRepository(db)

    async def get_all_companies(
        self,
        search: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[BusCompanyResponse]:
        """Search + Filter + Pagination ဖြင့် Company စာရင်းကို ပြန်ပေးသည်။"""
        companies, total = await self.repo.get_all(
            search=search,
            is_active=is_active,
            page=page,
            size=size,
        )
        total_pages = math.ceil(total / size) if total > 0 else 0
        items = [BusCompanyResponse.model_validate(c) for c in companies]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            size=size,
            total_pages=total_pages,
        )

    async def upload_company_logo(
        self, company_id: uuid.UUID, file: UploadFile
    ) -> BusCompanyResponse:

        company = await self.repo.get_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus company not found",
            )

        if company.logo_url:
            old_public_id = extract_public_id_from_url(company.logo_url)
            if old_public_id:
                await delete_from_cloudinary(old_public_id)

        new_logo_url = await upload_to_cloudinary(
            file=file,
            folder="companies",
        )
        update_data = BusCompanyUpdate(logo_url=new_logo_url)
        update_company = await self.repo.update(company, update_data)
        return update_company

    async def get_company_by_id(self, company_id: uuid.UUID) -> BusCompanyResponse:
        """Company ID ဖြင့် ရှာဖွေခြင်း (မရှိပါက 404 ပြမည်)"""
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus company not found",
            )
        return BusCompanyResponse.model_validate(company)

    async def create_company(self, data: BusCompanyCreate) -> BusCompanyResponse:
        """Company အသစ် ထည့်သွင်းခြင်း (အမည်တူရှိပါက 400 ပြမည်)"""
        existing = await self.repo.get_by_name(data.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bus company with name '{data.name}' already exists",
            )
        company = await self.repo.create(data)
        return BusCompanyResponse.model_validate(company)

    async def update_company(
        self, company_id: uuid.UUID, data: BusCompanyUpdate
    ) -> BusCompanyResponse:
        """Company အချက်အလက် ပြင်ဆင်ခြင်း"""
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus company not found",
            )

        # အမည်ပြောင်းလဲတော့မည်ဆိုလျှင် အမည်တူရှိမရှိ ထပ်စစ်ဆေးသည်
        if data.name is not None and data.name != company.name:
            existing = await self.repo.get_by_name(data.name)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Bus company with name '{data.name}' already exists",
                )

        updated = await self.repo.update(company, data)
        return BusCompanyResponse.model_validate(updated)

    async def delete_company(self, company_id: uuid.UUID) -> dict:
        """Company ဖျက်ထုတ်ခြင်း"""
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus company not found",
            )
        await self.repo.delete(company)
        # return {"message": "Bus company deleted successfully"}

    async def soft_delete_company(self, company_id: uuid.UUID) -> dict:
        company = await self.repo.get_by_id(company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bus company not found",
            )
        await self.repo.soft_delete(company.id)
        # return {"message": "Bus company deleted successfully"}
