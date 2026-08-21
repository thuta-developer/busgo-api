import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission, get_current_user
from app.models.user import User
from app.models.promotion import PromotionStatus
from app.schemas.promotion import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
    PromotionUsageResponse,
    ApplyPromotionRequest,
    ApplyPromotionResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.promo_service import PromotionService

router = APIRouter(prefix="/promotions", tags=["Promotions"])


# ================= Admin: Promotion Management =================


@router.get(
    "/",
    response_model=PaginatedResponse[PromotionResponse],
    dependencies=[Depends(has_permission("promotion:read"))],
)
async def list_promotions(
    search: Optional[str] = Query(None, description="Search by name or promo code"),
    status_filter: Optional[PromotionStatus] = Query(None, alias="status"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Promotion စာရင်းကို Pagination ဖြင့် ရယူခြင်း (Admin)
    """
    service = PromotionService(db)
    return await service.get_all_promotions(
        search=search,
        status_filter=status_filter,
        is_active=is_active,
        page=page,
        size=size,
    )


@router.get(
    "/active",
    response_model=list[PromotionResponse],
)
async def list_active_promotions(
    db: AsyncSession = Depends(get_db),
):
    """
    Active ဖြစ်နေသော Promotion များကို ရယူခြင်း (Public)
    """
    service = PromotionService(db)
    return await service.get_active_promotions()


@router.get(
    "/code/{promo_code}",
    response_model=PromotionResponse,
)
async def get_promotion_by_code(
    promo_code: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Promo Code ဖြင့် Promotion ရှာဖွေခြင်း (Public)
    """
    service = PromotionService(db)
    return await service.get_promotion_by_code(promo_code)


@router.get(
    "/{promotion_id}",
    response_model=PromotionResponse,
    dependencies=[Depends(has_permission("promotion:read"))],
)
async def get_promotion(
    promotion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Promotion ID ဖြင့် Promotion ရယူခြင်း
    """
    service = PromotionService(db)
    return await service.get_promotion(promotion_id)


@router.post(
    "/",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("promotion:create"))],
)
async def create_promotion(
    data: PromotionCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Promotion အသစ် ဖန်တီးခြင်း (Admin)
    Body: {
        "name": "Summer Sale",
        "promo_code": "SUMMER25",
        "discount_percentage": 25,
        "discount_amount": null,
        "max_usage": 100,
        "max_usage_per_user": 1,
        "expires_at": "2026-12-31T23:59:59Z"
    }
    """
    service = PromotionService(db)
    return await service.create_promotion(data)


@router.put(
    "/{promotion_id}",
    response_model=PromotionResponse,
    dependencies=[Depends(has_permission("promotion:update"))],
)
async def update_promotion(
    promotion_id: uuid.UUID,
    data: PromotionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Promotion အချက်အလက် ပြင်ဆင်ခြင်း (Admin)
    """
    service = PromotionService(db)
    return await service.update_promotion(promotion_id, data)


@router.delete(
    "/{promotion_id}",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(has_permission("promotion:delete"))],
)
async def delete_promotion(
    promotion_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Promotion ကို ဖျက်ခြင်း (Admin)
    """
    service = PromotionService(db)
    return await service.delete_promotion(promotion_id)


@router.patch(
    "/{promotion_id}/status",
    response_model=PromotionResponse,
    dependencies=[Depends(has_permission("promotion:update"))],
)
async def update_promotion_status(
    promotion_id: uuid.UUID,
    new_status: PromotionStatus,
    db: AsyncSession = Depends(get_db),
):
    """
    Promotion Status ကို Update လုပ်ခြင်း (Admin)
    Status: active, expired, disabled
    """
    service = PromotionService(db)
    return await service.update_promotion_status(promotion_id, new_status)


# ================= Apply / Validate Promotion =================


@router.post(
    "/apply",
    response_model=ApplyPromotionResponse,
)
async def apply_promotion(
    payload: ApplyPromotionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Promo Code ကို Validate လုပ်ပြီး Discount ကို တွက်ချက်ပေးခြင်း
    Body: {"promo_code": "SUMMER25", "booking_total": 50000}
    """
    service = PromotionService(db)
    return await service.apply_promotion(
        user_id=current_user.id,
        data=payload,
    )


# ================= Promotion Usage =================


@router.get(
    "/{promotion_id}/usages",
    response_model=PaginatedResponse[PromotionUsageResponse],
    dependencies=[Depends(has_permission("promotion:read"))],
)
async def get_promotion_usages(
    promotion_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Promotion တစ်ခုအတွက် Usage စာရင်း (Admin)
    """
    service = PromotionService(db)
    return await service.get_promotion_usages(
        promotion_id=promotion_id,
        page=page,
        size=size,
    )