import uuid
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.schemas.payment import PaymentCreate, PaymentUpdate


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        
        self.db = db

    async def create(self, data: PaymentCreate) -> Payment:
        payment = Payment(**data.model_dump())
        self.db.add(payment)
        await self.db.commit()
        # Re-fetch with booking relationship eagerly loaded to avoid MissingGreenlet
        return await self.get_by_id(payment.id)

    async def get_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.id == payment_id)
            .options(selectinload(Payment.booking))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_transaction_id(self, transaction_id: str) -> Optional[Payment]:
        stmt = select(Payment).where(Payment.transaction_id == transaction_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


    async def get_by_booking_id(self, booking_id: uuid.UUID) -> List[Payment]:
        stmt = select(Payment).where(Payment.booking_id == booking_id).order_by(Payment.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


    async def get_latest_by_booking_id(self, booking_id: uuid.UUID) -> Optional[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.booking_id == booking_id)
            .options(selectinload(Payment.booking))
            .order_by(Payment.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, payment: Payment, data: PaymentUpdate) -> Payment:
        for key, value in data.model_dump(exclude_unset=True).items():
            setattr(payment, key, value)
        await self.db.commit()
        # Re-fetch with booking relationship eagerly loaded to avoid MissingGreenlet
        return await self.get_by_id(payment.id)

    async def update_status(
        self,
        payment_id: uuid.UUID,
        status: PaymentStatus,
        transaction_id: Optional[str] = None, 
        gateway_data: Optional[dict] = None,
        paid_at: Optional[datetime] = None,
        refunded_at: Optional[datetime] = None,
        vendor: Optional[str] = None,
        gateway_method: Optional[str] = None
    ) -> Optional[Payment]:
        payment = await self.get_by_id(payment_id)
        if not payment:
            return None

        payment.status = status
        if transaction_id:
            payment.transaction_id = transaction_id
        if gateway_data:
            payment.gateway_data = gateway_data
        if paid_at:
            payment.paid_at = paid_at
        if refunded_at:
            payment.refunded_at = refunded_at
        if vendor:
            payment.vendor = vendor
        if gateway_method:
            payment.gateway_method = gateway_method
        
        await self.db.commit()
        # Re-fetch with booking relationship eagerly loaded to avoid MissingGreenlet
        return await self.get_by_id(payment_id)
