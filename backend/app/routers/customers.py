from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.orm import Customer, CustomerProfile, EmploymentRecord, IncomeRecord, BankAccount, KYCRecord, RiskProfile, User
from app.core.crypto import decrypt_field

router = APIRouter(prefix="/api/v1/customers", tags=["customers"])


@router.get("/profile/{customer_id}")
async def get_customer_profile(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    cust_stmt = select(Customer).where(Customer.id == uuid.UUID(customer_id))
    cust = (await db.execute(cust_stmt)).scalar_one_or_none()
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Enforce access control: customer can only view their own profile unless user is staff
    if current_user.role == "customer" and cust.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this customer profile")

    full_name = decrypt_field(cust.encrypted_full_name) if cust.encrypted_full_name else "Customer"
    address = decrypt_field(cust.encrypted_address) if cust.encrypted_address else ""

    # Load child entities
    prof_stmt = select(CustomerProfile).where(CustomerProfile.customer_id == cust.id)
    profile = (await db.execute(prof_stmt)).scalar_one_or_none()

    emp_stmt = select(EmploymentRecord).where(EmploymentRecord.customer_id == cust.id)
    emp = (await db.execute(emp_stmt)).scalar_one_or_none()

    inc_stmt = select(IncomeRecord).where(IncomeRecord.customer_id == cust.id)
    inc = (await db.execute(inc_stmt)).scalar_one_or_none()

    bank_stmt = select(BankAccount).where(BankAccount.customer_id == cust.id)
    bank = (await db.execute(bank_stmt)).scalar_one_or_none()

    risk_stmt = select(RiskProfile).where(RiskProfile.customer_id == cust.id)
    risk = (await db.execute(risk_stmt)).scalar_one_or_none()

    return {
        "customer_id": str(cust.id),
        "full_name": full_name,
        "address": address,
        "is_public_servant": cust.is_public_servant,
        "alesco_file_number": cust.alesco_file_number,
        "status": cust.status,
        "risk_flag": cust.risk_flag,
        "profile": {
            "province": profile.province if profile else None,
            "district": profile.district if profile else None,
            "gender": profile.gender if profile else None,
            "dependents_count": profile.dependents_count if profile else 0
        } if profile else None,
        "employment": {
            "employer_name": emp.employer_name if emp else None,
            "position": emp.position if emp else None,
            "pay_frequency": emp.pay_frequency if emp else None
        } if emp else None,
        "income": {
            "gross_fortnightly": float(inc.gross_income_fortnightly) if inc else 0.0,
            "net_fortnightly": float(inc.net_income_fortnightly) if inc else 0.0,
            "verified": inc.verified if inc else False
        } if inc else None,
        "bank_account": {
            "bank_name": bank.bank_name if bank else None,
            "account_name": bank.account_name if bank else None,
            "bsb_code": bank.bsb_code if bank else None
        } if bank else None,
        "risk_profile": {
            "risk_tier": risk.risk_tier if risk else "low",
            "risk_score": risk.risk_score if risk else 700,
            "max_approved_limit": float(risk.max_approved_limit) if risk else 10000.0
        } if risk else None
    }
