from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.models.orm import Loan, Customer
from app.services.agreement_service import AgreementService
from app.core.crypto import decrypt_field

router = APIRouter(prefix="/api/v1/agreements", tags=["agreements"])


class SignAgreementRequest(BaseModel):
    loan_id: str
    ip_address: str = "127.0.0.1"
    user_agent: str = "Mozilla/5.0"


@router.get("/loan/{loan_id}")
async def get_agreement(loan_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Loan).where(Loan.id == uuid.UUID(loan_id))
    loan = (await db.execute(stmt)).scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    cust_stmt = select(Customer).where(Customer.id == loan.customer_id)
    cust = (await db.execute(cust_stmt)).scalar_one_or_none()
    cust_name = decrypt_field(cust.encrypted_full_name) if cust and cust.encrypted_full_name else "Borrower"

    doc = AgreementService.generate_agreement_document(
        customer_name=cust_name,
        national_id_or_phone="PNG-REG-CUSTOMER",
        principal_amount=float(loan.principal_amount),
        periodic_repayment=float(loan.periodic_repayment),
        term_periods=loan.term_periods,
        compounding_period=loan.compounding_period,
        total_repayment=float(loan.total_repayment)
    )

    return doc


@router.post("/sign")
async def sign_agreement(body: SignAgreementRequest, db: AsyncSession = Depends(get_db)):
    sig = AgreementService.record_electronic_signature(
        agreement_id=body.loan_id,
        ip_address=body.ip_address,
        user_agent=body.user_agent
    )
    return {
        "status": "signed",
        "signature": sig
    }
