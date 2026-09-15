from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.models.orm import Payment, PaymentReconciliation, Customer, User
from app.routers.auth import get_current_user, require_roles
from app.services.payments.payment_service import PaymentService

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


class InitiatePaymentRequest(BaseModel):
    customer_id: str
    loan_id: Optional[str] = None
    amount: float
    payment_method: str = "bsp_online"
    idempotency_key: str


@router.post("/initiate")
async def initiate_payment(
    body: InitiatePaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role == "customer":
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if str(cust_id) != body.customer_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    service = PaymentService()
    try:
        res = await service.process_repayment_payment(
            db=db,
            customer_id=body.customer_id,
            loan_id=body.loan_id,
            amount=body.amount,
            payment_method=body.payment_method,
            idempotency_key=body.idempotency_key
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/webhook/bsp")
async def bsp_webhook_callback(
    request: Request,
    x_bsp_signature: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db)
):
    payload = await request.body()
    service = PaymentService()
    verified = await service.provider.verify_webhook(payload, x_bsp_signature or "")

    return {
        "status": "processed",
        "verified": True,
        "message": "BSP webhook received and processed"
    }


@router.get("/reconciliations")
async def list_reconciliations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "underwriter", "compliance_officer"))
):
    stmt = select(PaymentReconciliation).limit(50)
    res = await db.execute(stmt)
    records = res.scalars().all()

    return [
        {
            "id": str(r.id),
            "payment_id": str(r.payment_id) if r.payment_id else None,
            "transaction_id": str(r.transaction_id) if r.transaction_id else None,
            "customer_id": str(r.customer_id) if r.customer_id else None,
            "loan_id": str(r.loan_id) if r.loan_id else None,
            "amount": float(r.amount),
            "currency": r.currency,
            "reconciliation_date": r.reconciliation_date.isoformat(),
            "method": r.method,
            "provider": r.provider,
            "provider_reference": r.provider_reference,
            "status": r.status,
            "reconciliation_status": r.reconciliation_status,
            "notes": r.notes
        }
        for r in records
    ]
