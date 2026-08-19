import uuid
from typing import Optional
from fastapi import APIRouter, Depends, status, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, has_permission, get_current_user
from app.models.user import User
from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentResponse,
    PaymentCallbackRequest,
)
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/initiate",
    response_model=PaymentInitiateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(has_permission("payment:create"))],
)
async def initiate_payment(
    request: PaymentInitiateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    MyanMyanPay Payment ကို စတင်ခြင်း
    """
    service = PaymentService(db)
    return await service.initiate_payment(
        booking_id=request.booking_id,
        payment_method=request.method,
        return_url=str(request.return_url) if request.return_url else None,
        cancel_url=str(request.cancel_url) if request.cancel_url else None,
    )


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
)
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    MyanMyanPay က ပြန်ပို့တဲ့ Webhook ကို လက်ခံခြင်း
    """
    # Get raw body
    payload_str = await request.body()
    payload_str = payload_str.decode("utf-8")
    
    # Get headers
    nonce = request.headers.get("X-Mmpay-Nonce")
    signature = request.headers.get("X-Mmpay-Signature")
    
    if not nonce or not signature:
        raise HTTPException(status_code=400, detail="Missing required headers")
    
    service = PaymentService(db)
    result = await service.handle_webhook(payload_str, nonce, signature)
    return result


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
    dependencies=[Depends(has_permission("payment:read"))],
)
async def get_payment_status(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Payment Status ကို ပြန်ပေးခြင်း
    """
    service = PaymentService(db)
    return await service.get_payment_status(payment_id)


@router.post(
    "/{payment_id}/cancel",
    response_model=dict,
    dependencies=[Depends(has_permission("payment:update"))],
)
async def cancel_payment(
    payment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Payment ကို ပယ်ဖျက်ခြင်း
    """
    service = PaymentService(db)
    return await service.cancel_payment(payment_id)