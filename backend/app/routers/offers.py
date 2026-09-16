from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.models.orm import LoanOffer, LoanApplication, Loan, LoanSchedule, Transaction, Customer, User
from app.routers.auth import get_current_user, require_roles
from app.services.agreement_service import AgreementService
from app.services.calculation_engine import CalculationEngine
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/offers", tags=["offers"])

STAFF_ROLES = ("administrator", "admin", "owner", "underwriter", "collections_agent", "compliance_officer")


@router.get("/{id}")
async def get_offer(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(LoanOffer).where(LoanOffer.id == uuid.UUID(id))
    offer = (await db.execute(stmt)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    if current_user.role not in STAFF_ROLES:
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if offer.customer_id != cust_id:
            raise HTTPException(status_code=403, detail="Access denied")

    calc = CalculationEngine.calculate_loan_summary(
        principal_amount=float(offer.approved_amount),
        interest_rate_bp=offer.interest_rate_bp,
        compounding_period=offer.compounding_period,
        term_periods=offer.term_periods,
        admin_fee=float(offer.fees)
    )

    return {
        "id": str(offer.id),
        "application_id": str(offer.application_id),
        "approved_amount": float(offer.approved_amount),
        "interest_rate_bp": offer.interest_rate_bp,
        "term_periods": offer.term_periods,
        "compounding_period": offer.compounding_period,
        "periodic_repayment": float(offer.periodic_repayment),
        "total_repayment": float(offer.total_repayment),
        "total_interest": float(offer.total_interest),
        "fees": float(offer.fees),
        "status": offer.status,
        "expires_at": offer.expires_at,
        "schedule": calc["schedule"]
    }


@router.post("/{id}/accept")
async def accept_offer(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(LoanOffer).where(LoanOffer.id == uuid.UUID(id))
    offer = (await db.execute(stmt)).scalar_one_or_none()
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    if current_user.role not in STAFF_ROLES:
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if offer.customer_id != cust_id:
            raise HTTPException(status_code=403, detail="Access denied")

    offer.status = "accepted"

    # Update application state
    app_stmt = select(LoanApplication).where(LoanApplication.id == offer.application_id)
    app_obj = (await db.execute(app_stmt)).scalar_one_or_none()
    if app_obj:
        app_obj.status = "offer_accepted"

    # Create active loan upon offer acceptance
    loan = Loan(
        customer_id=offer.customer_id,
        application_id=offer.application_id,
        offer_id=offer.id,
        principal_amount=offer.approved_amount,
        interest_rate_bp=offer.interest_rate_bp,
        compounding_period=offer.compounding_period,
        term_periods=offer.term_periods,
        periodic_repayment=offer.periodic_repayment,
        total_repayment=offer.total_repayment,
        outstanding_balance=offer.approved_amount,
        calculation_methodology=offer.calculation_methodology or "reducing_balance",
        calculation_snapshot=offer.calculation_snapshot,
        status="active"
    )
    db.add(loan)
    await db.flush()

    # Generate schedule
    calc = CalculationEngine.calculate_loan_summary(
        principal_amount=float(offer.approved_amount),
        interest_rate_bp=offer.interest_rate_bp,
        compounding_period=offer.compounding_period,
        term_periods=offer.term_periods,
        admin_fee=float(offer.fees)
    )

    for item in calc["schedule"]:
        from datetime import datetime
        s_date = datetime.fromisoformat(item["due_date"]).date()
        db.add(LoanSchedule(
            loan_id=loan.id,
            instalment_number=item["instalment_number"],
            due_date=s_date,
            principal_due=item["principal_due"],
            interest_due=item["interest_due"],
            fee_due=item["fee_due"],
            total_due=item["total_due"],
            status="pending"
        ))

    # Initial ledger entry
    db.add(Transaction(
        loan_id=loan.id,
        type="disbursement",
        amount=offer.approved_amount,
        balance_after=offer.approved_amount,
        notes="Online loan accepted and disbursed.",
        idempotency_key=f"DISB-{loan.id}"
    ))

    await AuditService.log_event(
        db=db,
        action="LOAN_OFFER_ACCEPTED",
        entity_type="LOAN_OFFER",
        entity_id=str(offer.id),
        customer_id=str(offer.customer_id)
    )

    await db.commit()

    return {
        "offer_id": str(offer.id),
        "status": offer.status,
        "loan_id": str(loan.id),
        "message": "Loan offer accepted and loan created successfully."
    }
