import uuid
import json
import secrets
import httpx
import hmac
import hashlib
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.booking import Booking, BookingStatus
from app.models.promotion_usage import UsageStatus
from app.repositories.payment_repository import PaymentRepository
from app.repositories.booking_repository import BookingRepository
from app.services.promo_service import PromotionService
from app.schemas.payment import (
    PaymentCreate,
    PaymentUpdate,
    PaymentResponse,
    PaymentInitiateRequest,
    PaymentInitiateResponse,
    PaymentCallbackRequest,
)

# MyanMyanPay SDK
from mmpay import MMPaySDK
from mmpay.types import PaymentRequest, PayGetRequest, PayCancelRequest

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.payment_repo = PaymentRepository(db)
        self.booking_repo = BookingRepository(db)
        self.promo_service = PromotionService(db)

        self.mmpay = MMPaySDK(
            {
                "appId": settings.MYANMYANPAY_APP_ID.strip(),
                "publishableKey": settings.MYANMYANPAY_PUBLISHABLE_KEY.strip(),
                "secretKey": settings.MYANMYANPAY_SECRET_KEY.strip(),
                "apiBaseUrl": settings.MYANMYANPAY_API_BASE_URL.strip(),
            }
        )

    # ==============================================
    # Helper Methods
    # ==============================================
    def _generate_order_id(self, booking_code: str) -> str:
        return f"BUSGO-{booking_code}"

    def _calculate_expiry(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            minutes=settings.PAYMENT_EXPIRY_MINUTES
        )

    async def _update_payment_from_gateway_response(
        self,
        payment: Payment,
        gateway_response: dict,
        status: PaymentStatus,
        transaction_id: Optional[str] = None,
        paid_at: Optional[datetime] = None,
        refunded_at: Optional[datetime] = None,
    ) -> Payment:
        update_data = PaymentUpdate(
            status=status,
            transaction_id=transaction_id or gateway_response.get("transactionRefId"),
            gateway_data=gateway_response,
            paid_at=paid_at,
            refunded_at=refunded_at,
            vendor=gateway_response.get("vendor"),
            gateway_method=gateway_response.get("method"),
        )
        return await self.payment_repo.update(payment, update_data)

    async def _record_successful_promotion_usage(self, booking: Booking) -> None:
        """Record promotion usage only after the booking payment succeeds."""
        if not booking.promotion_id:
            return

        existing_usage = await self.promo_service.repo.get_usage_by_booking(booking.id)
        if existing_usage:
            return

        await self.promo_service.record_usage(
            promotion_id=booking.promotion_id,
            user_id=booking.user_id,
            booking_id=booking.id,
            discount_amount_applied=float(booking.discount_amount),
            status=UsageStatus.SUCCESS,
        )

    # ==============================================
    # Initiate Payment
    # ==============================================
    async def initiate_payment(
        self,
        booking_id: uuid.UUID,
        payment_method: PaymentMethod = PaymentMethod.MYANMYANPAY,
        return_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> PaymentInitiateResponse:
        booking = await self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        existing_payment = await self.payment_repo.get_latest_by_booking_id(booking_id)
        if existing_payment and existing_payment.status == PaymentStatus.PENDING:
            return PaymentInitiateResponse(
                payment_id=existing_payment.id,
                booking_id=booking_id,
                transaction_id=existing_payment.transaction_id or "",
                qr_code=existing_payment.payment_url or "",
                payment_url=existing_payment.payment_url or "",
                expiry_date=existing_payment.expiry_date or datetime.now(timezone.utc),
                amount=existing_payment.amount,
                currency=existing_payment.currency,
                status=existing_payment.status,
                vendor=existing_payment.vendor,
            )

        order_id = self._generate_order_id(booking.booking_code)
        payment = await self.payment_repo.create(
            PaymentCreate(
                booking_id=booking.id,
                amount=booking.net_amount,
                currency="MMK",
                method=payment_method,
            )
        )

        try:
            # SDK သို့ ပို့မည့် Payload Structure
            pay_req: PaymentRequest = {
                "orderId": order_id,
                "amount": int(booking.net_amount),
                "currency": "MMK",
                "callbackUrl": settings.MMPAY_WEBHOOK_URL
                or f"{settings.BASE_URL}/api/v1/payments/webhook",
                "customMessage": f"Booking: {booking.booking_code}",
                "items": [
                    {
                        "name": f"Bus Ticket - {booking.booking_code}",
                        "amount": int(booking.net_amount),
                        "quantity": 1,
                    }
                ],
            }

            if return_url:
                pay_req["returnUrl"] = return_url
            if cancel_url:
                pay_req["cancelUrl"] = cancel_url

            response = self.mmpay.pay(pay_req)
            qr_string = response.get("qr", "")
            ref_id = (
                response.get("vendorQrRefId")
                or response.get("transactionRefId")
                or order_id
            )

            payment = await self.payment_repo.update(
                payment,
                PaymentUpdate(
                    status=PaymentStatus.PENDING,
                    transaction_id=ref_id,
                    gateway_data=response,
                    vendor=response.get("vendor"),
                    gateway_method=response.get("method"),
                ),
            )
            payment.payment_url = qr_string
            await self.db.commit()

            return PaymentInitiateResponse(
                payment_id=payment.id,
                booking_id=booking_id,
                transaction_id=payment.transaction_id or "",
                qr_code=qr_string,
                payment_url=qr_string,
                expiry_date=self._calculate_expiry(),
                amount=payment.amount,
                currency=payment.currency,
                status=payment.status,
                vendor=payment.vendor,
            )

        except Exception as e:
            logger.error(f"MyanMyanPay initialization error: {str(e)}")
            await self.payment_repo.update_status(
                payment.id, PaymentStatus.FAILED, gateway_data={"error": str(e)}
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Payment gateway error: {str(e)}",
            )

    # ==============================================
    # Webhook Handler
    # ==============================================

    async def handle_webhook(
        self, payload_str: str, nonce: str, signature: str
    ) -> dict:
        try:
            if not self.mmpay.verify_cb(payload_str, nonce, signature):
                raise HTTPException(status_code=400, detail="Invalid signature")

            payload = json.loads(payload_str)
            order_id = payload.get("orderId")
            gate_status = payload.get("status")
            if not order_id:
                raise HTTPException(status_code=400, detail="Missing orderId")

            booking_code = order_id.replace("BUSGO-", "").replace("BusGo-", "")
            booking = await self.booking_repo.get_by_code(booking_code)
            if not booking:
                return {"status": "error", "message": "Booking not found"}

            payment = await self.payment_repo.get_latest_by_booking_id(booking.id)
            if not payment:
                return {"status": "error", "message": "Payment not found"}

            status_map = {
                "SUCCESS": (PaymentStatus.PAID, BookingStatus.CONFIRMED),
                "CANCELLED": (PaymentStatus.CANCELLED, BookingStatus.CANCELLED),
                "FAILED": (PaymentStatus.FAILED, BookingStatus.PENDING),
                "EXPIRED": (PaymentStatus.EXPIRED, BookingStatus.PAYMENT_EXPIRED),
                "REFUNDED": (PaymentStatus.REFUNDED, BookingStatus.REFUNDED),
            }

            p_status, b_status = status_map.get(
                gate_status, (payment.status, booking.status)
            )

            await self._update_payment_from_gateway_response(
                payment=payment,
                gateway_response=payload,
                status=p_status,
                transaction_id=payload.get("transactionRefId"),
                paid_at=(
                    datetime.now(timezone.utc) if gate_status == "SUCCESS" else None
                ),
                refunded_at=(
                    datetime.now(timezone.utc) if gate_status == "REFUNDED" else None
                ),
            )

            booking.status = b_status
            if gate_status == "SUCCESS":
                await self._record_successful_promotion_usage(booking)
            await self.db.commit()
            return {"status": "success", "message": "Webhook processed successfully"}
        except Exception as e:
            logger.error(f"Webhook processing failure: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    # ==============================================
    # Get Payment Status
    # ==============================================

    async def get_payment_status(self, payment_id: uuid.UUID) -> PaymentResponse:
        """Payment Status ကို ပြန်ပေးခြင်း"""
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        # If payment is still pending, check with gateway
        if payment.status == PaymentStatus.PENDING:
            try:
                # Call MyanMyanPay to get latest status
                order_id = self._generate_order_id(payment.booking.booking_code)
                get_payload: PayGetRequest = {"orderId": order_id}
                response = self.mmpay.get(get_payload)

                gateway_status = response.get("status")
                vendor = response.get("vendor")
                gateway_method = response.get("method")

                if gateway_status == "SUCCESS":
                    await self._update_payment_from_gateway_response(
                        payment=payment,
                        gateway_response=response,
                        status=PaymentStatus.PAID,
                        transaction_id=response.get("transactionRefId"),
                        paid_at=datetime.now(timezone.utc),
                    )
                    # Update booking
                    booking = payment.booking
                    booking.status = BookingStatus.CONFIRMED
                    await self._record_successful_promotion_usage(booking)
                    await self.db.commit()

                elif gateway_status == "CANCELLED":
                    await self._update_payment_from_gateway_response(
                        payment=payment,
                        gateway_response=response,
                        status=PaymentStatus.CANCELLED,
                    )
                    booking = payment.booking
                    booking.status = BookingStatus.CANCELLED
                    await self.db.commit()

                elif gateway_status in ["FAILED", "EXPIRED"]:
                    payment_status = (
                        PaymentStatus.EXPIRED
                        if gateway_status == "EXPIRED"
                        else PaymentStatus.FAILED
                    )
                    await self._update_payment_from_gateway_response(
                        payment=payment,
                        gateway_response=response,
                        status=payment_status,
                    )
                    booking = payment.booking
                    booking.status = (
                        BookingStatus.EXPIRED
                        if gateway_status == "EXPIRED"
                        else BookingStatus.PENDING
                    )
                    await self.db.commit()

                # Refresh payment
                payment = await self.payment_repo.get_by_id(payment_id)

            except Exception as e:
                logger.warning(f"Failed to check payment status with gateway: {str(e)}")

        return PaymentResponse.model_validate(payment)

    # ==============================================
    # Cancel Payment
    # ==============================================

    async def cancel_payment(self, payment_id: uuid.UUID) -> dict:
        """
        MyanMyanPay Payment ကို ပယ်ဖျက်ခြင်း
        """
        payment = await self.payment_repo.get_by_id(payment_id)
        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.status not in [
            PaymentStatus.PENDING,
            PaymentStatus.AWAITING_PAYMENT,
        ]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel payment with status: {payment.status}",
            )

        try:
            order_id = self._generate_order_id(payment.booking.booking_code)
            cancel_payload: PayCancelRequest = {"orderId": order_id}
            response = self.mmpay.cancel(cancel_payload)

            # Update payment status
            await self._update_payment_from_gateway_response(
                payment=payment,
                gateway_response=response,
                status=PaymentStatus.CANCELLED,
            )

            # Update booking status
            booking = payment.booking
            booking.status = BookingStatus.CANCELLED
            await self.db.commit()

            return {
                "status": "success",
                "message": "Payment cancelled successfully",
                "payment_id": str(payment.id),
                "order_id": order_id,
            }

        except Exception as e:
            logger.error(f"Failed to cancel payment: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to cancel payment: {str(e)}",
            )
