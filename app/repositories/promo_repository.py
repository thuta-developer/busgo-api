from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.promotion import Promotion, PromotionStatus
from app.models.promotion_usage import PromotionUsage, UsageStatus
from app.schemas.promotion import PromotionCreate, PromotionUpdate


class PromotionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========== Promotion CRUD ==========

    async def get_by_id(self, promotion_id: UUID) -> Optional[Promotion]:
        stmt = (
            select(Promotion)
            .where(Promotion.id == promotion_id)
            .options(selectinload(Promotion.usages))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, promo_code: str) -> Optional[Promotion]:
        stmt = (
            select(Promotion)
            .where(Promotion.promo_code == promo_code.upper())
            .options(selectinload(Promotion.usages))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        search: Optional[str] = None,
        status: Optional[PromotionStatus] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Promotion], int]:
        query = select(Promotion)
        if search:
            query = query.where(
                or_(
                    Promotion.name.ilike(f"%{search}%"),
                    Promotion.promo_code.ilike(f"%{search}%"),
                )
            )
        if status:
            query = query.where(Promotion.status == status)
        if is_active is not None:
            query = query.where(Promotion.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()

        query = (
            query.options(selectinload(Promotion.usages))
            .order_by(desc(Promotion.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create(self, data: PromotionCreate) -> Promotion:
        promotion = Promotion(
            name=data.name,
            description=data.description,
            promo_code=data.promo_code.upper(),
            discount_percentage=data.discount_percentage,
            discount_amount=data.discount_amount,
            max_usage=data.max_usage,
            max_usage_per_user=data.max_usage_per_user,
            expires_at=data.expires_at,
            is_active=data.is_active,
        )
        self.db.add(promotion)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError(f"Promo code '{data.promo_code}' already exists")
        return await self.get_by_id(promotion.id)

    async def update(self, promotion: Promotion, data: PromotionUpdate) -> Promotion:
        update_data = data.model_dump(exclude_unset=True)
        if "promo_code" in update_data and update_data["promo_code"]:
            update_data["promo_code"] = update_data["promo_code"].upper()
        for key, value in update_data.items():
            setattr(promotion, key, value)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("Promo code already exists")
        return await self.get_by_id(promotion.id)

    async def delete(self, promotion_id: UUID) -> bool:
        promotion = await self.get_by_id(promotion_id)
        if not promotion:
            return False
        await self.db.delete(promotion)
        await self.db.commit()
        return True

    async def update_status(
        self, promotion_id: UUID, status: PromotionStatus
    ) -> Optional[Promotion]:
        promotion = await self.get_by_id(promotion_id)
        if not promotion:
            return None
        promotion.status = status
        await self.db.commit()
        return await self.get_by_id(promotion_id)

    # ========== Promotion Usage ==========

    async def get_user_usage_count(
        self, user_id: UUID, promotion_id: UUID, status: Optional[UsageStatus] = None
    ) -> int:
        stmt = select(func.count()).where(
            and_(
                PromotionUsage.user_id == user_id,
                PromotionUsage.promotion_id == promotion_id,
            )
        )
        if status:
            stmt = stmt.where(PromotionUsage.status == status)
        return (await self.db.execute(stmt)).scalar_one()

    async def get_total_usage_count(self, promotion_id: UUID) -> int:
        stmt = select(func.count()).where(PromotionUsage.promotion_id == promotion_id)
        return (await self.db.execute(stmt)).scalar_one()

    async def create_usage(
        self,
        promotion_id: UUID,
        user_id: UUID,
        booking_id: Optional[UUID] = None,
        discount_amount_applied: float = 0.0,
        status: UsageStatus = UsageStatus.PENDING,
    ) -> PromotionUsage:
        usage = PromotionUsage(
            promotion_id=promotion_id,
            user_id=user_id,
            booking_id=booking_id,
            discount_amount_applied=discount_amount_applied,
            status=status,
        )
        self.db.add(usage)
        await self.db.commit()
        return usage

    async def update_usage_status(
        self, usage_id: UUID, status: UsageStatus, booking_id: Optional[UUID] = None
    ) -> Optional[PromotionUsage]:
        usage = await self.get_usage_by_id(usage_id)
        if not usage:
            return None
        usage.status = status
        if booking_id:
            usage.booking_id = booking_id
        await self.db.commit()
        return usage

    async def get_usage_by_id(self, usage_id: UUID) -> Optional[PromotionUsage]:
        stmt = (
            select(PromotionUsage)
            .where(PromotionUsage.id == usage_id)
            .options(
                selectinload(PromotionUsage.promotion).selectinload(Promotion.usages),
                selectinload(PromotionUsage.user),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_usages_by_promotion(
        self, promotion_id: UUID, page: int = 1, size: int = 20
    ) -> Tuple[List[PromotionUsage], int]:
        query = select(PromotionUsage).where(
            PromotionUsage.promotion_id == promotion_id
        )
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar_one()
        query = (
            query.options(
                selectinload(PromotionUsage.promotion).selectinload(Promotion.usages),
                selectinload(PromotionUsage.user),
                selectinload(PromotionUsage.booking),
            )
            .order_by(desc(PromotionUsage.created_at))
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def get_usage_by_booking(self, booking_id: UUID) -> Optional[PromotionUsage]:
        stmt = (
            select(PromotionUsage)
            .where(PromotionUsage.booking_id == booking_id)
            .options(
                selectinload(PromotionUsage.promotion),
                selectinload(PromotionUsage.user),
            )
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_active_promotions(self) -> List[Promotion]:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Promotion)
            .where(
                and_(
                    Promotion.is_active == True,
                    Promotion.status == PromotionStatus.ACTIVE,
                    Promotion.expires_at > now,
                )
            )
            .options(selectinload(Promotion.usages))
            .order_by(desc(Promotion.created_at))
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
