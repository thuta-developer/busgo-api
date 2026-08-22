import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession


from app.api.deps import get_db, has_permission
from app.schemas.bus_company import BusCompanyCreate, BusCompanyUpdate, BusCompanyResponse
from app.schemas.common import PaginatedResponse
from app.services.bus_company_service import BusCompanyService

router = APIRouter(prefix="/bus-companies", tags=["Bus Companies Management"])

@router.get(
    "/",
    response_model=PaginatedResponse[BusCompanyResponse],
    dependencies=[Depends(has_permission("bus_company:read"))],
)
async def list_companies(
    search: Optional[str] = Query(None, description="Search by name, email, phone, or address"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    service = BusCompanyService(db)
    return await service.get_all_companies(
        search=search,
        is_active=is_active,
        page=page,
        size=size,
    )


@router.get(
    "/{company_id}",
    response_model=BusCompanyResponse,
    dependencies=[Depends(has_permission("bus_company:read"))],
)
async def get_company(company_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    service = BusCompanyService(db)
    return await service.get_company_by_id(company_id)


@router.post(
    "/",
    response_model=BusCompanyResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("bus_company:create"))],
)
async def create_company(data: BusCompanyCreate, db: AsyncSession = Depends(get_db)):
    service = BusCompanyService(db)
    return await service.create_company(data)


@router.put(
    "/{company_id}",
    response_model=BusCompanyResponse,
    dependencies=[Depends(has_permission("bus_company:update"))],
)
async def update_company(
    company_id: uuid.UUID, data: BusCompanyUpdate, db: AsyncSession = Depends(get_db)
):
    service = BusCompanyService(db)
    return await service.update_company(company_id, data)


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("bus_company:delete"))],
)
async def delete_company(company_id: uuid.UUID, hard_delete: bool = Query(False, description="Permanently delete (default: soft delete)")  ,db: AsyncSession = Depends(get_db)):
    service = BusCompanyService(db)
    if hard_delete:
        await service.delete_company(company_id)
    else:
        await service.soft_delete_company(company_id)

    return {
        "message": f"Bus company {'hard ' if hard_delete else 'soft '}deleted successfully"
    }



@router.post(
    "/{company_id}/logo",
    response_model=BusCompanyResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("bus_company:update"))],
)
async def upload_logo(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    service = BusCompanyService(db)
    return await service.upload_company_logo(company_id=company_id, file=file)