from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.promo_repository import PromotionRepository
from app.repositories.user_repository import UserRepository
from app.models.promotion import Promotion, PromotionStatus
from app.models.promotion_usage import PromotionUsage, UsageStatus
from app.schemas.promotion import (
    PromotionCreate,
    PromotionUpdate,
    PromotionResponse,
    PromotionUsageResponse,
    PromotionUsageCreate,
    ApplyPromotionRequest,
    ApplyPromotionResponse,
)
from app.schemas.common import PaginatedResponse


class PromotionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PromotionRepository(db)
        self.user_repo = UserRepository(db)

    # ============================================
    # VALIDATION HELPERS
    # ============================================

    def _validate_promotion(self, promotion: Promotion) -> None:
        """Validate promotion is active, not expired, and not fully used."""
        if not promotion.is_active or promotion.status != PromotionStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This promotion is not active",
            )

        if promotion.is_expired:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This promotion has expired",
            )

        if promotion.is_fully_used:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This promotion has reached its usage limit",
            )

    async def _validate_user_usage(self, user_id: UUID, promotion_id: UUID) -> None:
        """Validate user hasn't exceeded max usage for this promotion."""
        usage_count = await self.repo.get_user_usage_count(
            user_id=user_id,
            promotion_id=promotion_id,
            status=UsageStatus.SUCCESS,
        )
        promotion = await self.repo.get_by_id(promotion_id)
        if promotion and usage_count >= promotion.max_usage_per_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"You have already used this promotion {usage_count} time(s)",
            )

    def _calculate_discount(
        self, promotion: Promotion, booking_total: float
    ) -> float:
        """Calculate discount amount based on promotion type."""
        if promotion.discount_percentage is not None:
            return round(booking_total * promotion.discount_percentage / 100, 2)
        if promotion.discount_amount is not None:
            return min(promotion.discount_amount, booking_total)
        return 0.0

    # ============================================
    # PROMOTION CRUD
    # ============================================

    async def create_promotion(self, data: PromotionCreate) -> PromotionResponse:
        """Promotion အသစ် ဖန်တီးခြင်း"""
        try:
            promotion = await self.repo.create(data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        return await self._to_response(promotion)

    async def get_promotion(self, promotion_id: UUID) -> PromotionResponse:
        """Promotion တစ်ခုကို ရယူခြင်း"""
        promotion = await self.repo.get_by_id(promotion_id)
        if not promotion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion not found",
            )
        return await self._to_response(promotion)

    async def get_promotion_by_code(self, promo_code: str) -> PromotionResponse:
        """Promo Code ဖြင့် Promotion ရှာဖွေခြင်း"""
        promotion = await self.repo.get_by_code(promo_code)
        if not promotion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion not found",
            )
        return await self._to_response(promotion)

    async def get_all_promotions(
        self,
        search: Optional[str] = None,
        status_filter: Optional[PromotionStatus] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> PaginatedResponse[PromotionResponse]:
        """Promotion စာရင်းကို Pagination ဖြင့် ရယူခြင်း"""
        promotions, total = await self.repo.get_all(
            search=search,
            status=status_filter,
            is_active=is_active,
            page=page,
            size=size,
        )
        items = [await self._to_response(p) for p in promotions]
        total_pages = (total + size - 1) // size if total > 0 else 0
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def update_promotion(
        self, promotion_id: UUID, data: PromotionUpdate
    ) -> PromotionResponse:
        """Promotion အချက်အလက် ပြင်ဆင်ခြင်း"""
        promotion = await self.repo.get_by_id(promotion_id)
        if not promotion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion not found",
            )
        try:
            promotion = await self.repo.update(promotion, data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e),
            )
        return await self._to_response(promotion)

    async def delete_promotion(self, promotion_id: UUID) -> dict:
        """Promotion ကို ဖျက်ခြင်း"""
        deleted = await self.repo.delete(promotion_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion not found",
            )
        return {"message": "Promotion deleted successfully"}

    async def update_promotion_status(
        self, promotion_id: UUID, new_status: PromotionStatus
    ) -> PromotionResponse:
        """Promotion Status ကို Update လုပ်ခြင်း"""
        promotion = await self.repo.update_status(promotion_id, new_status)
        if not promotion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion not found",
            )
        return await self._to_response(promotion)

    # ============================================
    # APPLY / VALIDATE PROMOTION
    # ============================================

    async def apply_promotion(
        self, user_id: UUID, data: ApplyPromotionRequest
    ) -> ApplyPromotionResponse:
        """
        Promo Code ကို Validate လုပ်ပြီး Discount ကို တွက်ချက်ပေးခြင်း။
        Booking မဖန်တီးမီ ကြိုတင် စစ်ဆေးရန် သုံးသည်။
        """
        promotion = await self.repo.get_by_code(data.promo_code)
        if not promotion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid promo code",
            )

        # Validate promotion
        self._validate_promotion(promotion)

        # Validate user usage
        await self._validate_user_usage(user_id, promotion.id)

        # Calculate discount
        discount = self._calculate_discount(promotion, data.booking_total)
        final_total = max(data.booking_total - discount, 0)

        return ApplyPromotionResponse(
            promotion_id=promotion.id,
            promo_code=promotion.promo_code,
            promotion_name=promotion.name,
            discount_percentage=promotion.discount_percentage,
            discount_amount=promotion.discount_amount,
            discount_applied=discount,
            final_total=final_total,
            is_valid=True,
            message="Promotion applied successfully",
        )

    # ============================================
    # PROMOTION USAGE
    # ============================================

    async def record_usage(
        self,
        promotion_id: UUID,
        user_id: UUID,
        booking_id: Optional[UUID] = None,
        discount_amount_applied: float = 0.0,
        status: UsageStatus = UsageStatus.PENDING,
    ) -> PromotionUsage:
        """Promotion Usage Record ဖန်တီးခြင်း"""
        return await self.repo.create_usage(
            promotion_id=promotion_id,
            user_id=user_id,
            booking_id=booking_id,
            discount_amount_applied=discount_amount_applied,
            status=status,
        )

    async def confirm_usage(
        self, usage_id: UUID, booking_id: UUID
    ) -> PromotionUsageResponse:
        """Promotion Usage ကို SUCCESS အဖြစ် အတည်ပြုခြင်း"""
        usage = await self.repo.update_usage_status(
            usage_id=usage_id,
            status=UsageStatus.SUCCESS,
            booking_id=booking_id,
        )
        if not usage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion usage not found",
            )
        return await self._usage_to_response(usage)

    async def cancel_usage(self, usage_id: UUID) -> PromotionUsageResponse:
        """Promotion Usage ကို CANCELLED အဖြစ် ပြောင်းခြင်း"""
        usage = await self.repo.update_usage_status(
            usage_id=usage_id,
            status=UsageStatus.CANCELLED,
        )
        if not usage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Promotion usage not found",
            )
        return await self._usage_to_response(usage)

    async def get_promotion_usages(
        self, promotion_id: UUID, page: int = 1, size: int = 20
    ) -> PaginatedResponse[PromotionUsageResponse]:
        """Promotion တစ်ခုအတွက် Usage စာရင်း"""
        usages, total = await self.repo.get_usages_by_promotion(
            promotion_id=promotion_id, page=page, size=size
        )
        items = [await self._usage_to_response(u) for u in usages]
        total_pages = (total + size - 1) // size if total > 0 else 0
        return PaginatedResponse(
            items=items, total=total, page=page, size=size, total_pages=total_pages
        )

    async def get_active_promotions(self) -> List[PromotionResponse]:
        """Active ဖြစ်နေသော Promotion များကို ရယူခြင်း"""
        promotions = await self.repo.get_active_promotions()
        return [await self._to_response(p) for p in promotions]

    # ============================================
    # RESPONSE HELPERS
    # ============================================

    async def _to_response(self, promotion: Promotion) -> PromotionResponse:
        """Promotion model ကို Response schema အဖြစ် ပြောင်းခြင်း"""
        response = PromotionResponse.model_validate(promotion)
        response.current_usage_count = promotion.current_usage_count
        response.is_expired = promotion.is_expired
        response.is_fully_used = promotion.is_fully_used
        return response

    async def _usage_to_response(
        self, usage: PromotionUsage
    ) -> PromotionUsageResponse:
        """PromotionUsage model ကို Response schema အဖြစ် ပြောင်းခြင်း"""
        response = PromotionUsageResponse.model_validate(usage)
        if usage.promotion:
            response.promotion = await self._to_response(usage.promotion)
        if usage.user:
            response.user_email = usage.user.email
        return response