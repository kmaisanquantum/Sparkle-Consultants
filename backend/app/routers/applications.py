from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.routers.auth import get_current_user
from app.models.orm import LoanApplication, Customer, LoanProduct, DecisionRecord, LoanOffer, User, IncomeRecord
from app.services.credit_decision_engine import CreditDecisionEngine
from app.services.offer_service import OfferService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])

STAFF_ROLES = ("administrator", "admin", "owner", "underwriter", "collections_agent", "compliance_officer")


class ApplicationDraftCreate(BaseModel):
    loan_product_id: Optional[str] = None
    amount_requested: float
    term_requested: int
    compounding_period: str = "fortnightly"
    purpose: Optional[str] = None
    step_completed: int = 1
    draft_data: Optional[Dict[str, Any]] = None


@router.post("/draft")
async def save_application_draft(
    body: ApplicationDraftCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cust_stmt = select(Customer).where(Customer.user_id == current_user.id)
    cust = (await db.execute(cust_stmt)).scalar_one_or_none()
    if not cust:
        tenant_id = current_user.tenant_id
        if not tenant_id:
            from app.models.orm import Tenant
            tenant = (await db.execute(select(Tenant).limit(1))).scalar_one_or_none()
            tenant_id = tenant.id if tenant else uuid.uuid4()

        from app.core.crypto import encrypt_field, hash_phone
        cust = Customer(
            tenant_id=tenant_id,
            user_id=current_user.id,
            phone_hash=hash_phone(current_user.email),
            encrypted_full_name=encrypt_field(current_user.full_name),
            status="active"
        )
        db.add(cust)
        await db.flush()

    app_stmt = select(LoanApplication).where(
        LoanApplication.customer_id == cust.id,
        LoanApplication.status == "draft"
    )
    existing_app = (await db.execute(app_stmt)).scalar_one_or_none()

    if existing_app:
        existing_app.amount_requested = body.amount_requested
        existing_app.term_requested = body.term_requested
        existing_app.compounding_period = body.compounding_period
        existing_app.purpose = body.purpose
        existing_app.step_completed = body.step_completed
        existing_app.draft_data = body.draft_data
        if body.loan_product_id:
            existing_app.loan_product_id = uuid.UUID(body.loan_product_id)
        app_obj = existing_app
    else:
        app_obj = LoanApplication(
            tenant_id=cust.tenant_id,
            customer_id=cust.id,
            loan_product_id=uuid.UUID(body.loan_product_id) if body.loan_product_id else None,
            amount_requested=body.amount_requested,
            term_requested=body.term_requested,
            compounding_period=body.compounding_period,
            purpose=body.purpose,
            step_completed=body.step_completed,
            status="draft",
            draft_data=body.draft_data
        )
        db.add(app_obj)

    await db.commit()
    await db.refresh(app_obj)

    return {
        "application_id": str(app_obj.id),
        "customer_id": str(cust.id),
        "status": app_obj.status,
        "step_completed": app_obj.step_completed,
        "message": "Application draft saved successfully"
    }


@router.get("/{id}")
async def get_application(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(LoanApplication).where(LoanApplication.id == uuid.UUID(id))
    app_obj = (await db.execute(stmt)).scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Loan application not found")

    if current_user.role not in STAFF_ROLES:
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if app_obj.customer_id != cust_id:
            raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": str(app_obj.id),
        "customer_id": str(app_obj.customer_id),
        "amount_requested": float(app_obj.amount_requested),
        "term_requested": app_obj.term_requested,
        "compounding_period": app_obj.compounding_period,
        "purpose": app_obj.purpose,
        "step_completed": app_obj.step_completed,
        "status": app_obj.status,
        "draft_data": app_obj.draft_data,
        "created_at": app_obj.created_at
    }


@router.post("/{id}/submit")
async def submit_application(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(LoanApplication).where(LoanApplication.id == uuid.UUID(id))
    app_obj = (await db.execute(stmt)).scalar_one_or_none()
    if not app_obj:
        raise HTTPException(status_code=404, detail="Loan application not found")

    if current_user.role not in STAFF_ROLES:
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if app_obj.customer_id != cust_id:
            raise HTTPException(status_code=403, detail="Access denied")

    # Fetch configured LoanProduct rules
    product = None
    if app_obj.loan_product_id:
        prod_stmt = select(LoanProduct).where(LoanProduct.id == app_obj.loan_product_id)
        product = (await db.execute(prod_stmt)).scalar_one_or_none()

    if not product:
        prod_stmt = select(LoanProduct).where(LoanProduct.is_active == True).limit(1)
        product = (await db.execute(prod_stmt)).scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=400, detail="No active loan product available for application evaluation")

    app_obj.status = "submitted"
    app_obj.step_completed = 17

    # Fetch customer's verified income or draft income data
    inc_stmt = select(IncomeRecord).where(IncomeRecord.customer_id == app_obj.customer_id)
    income = (await db.execute(inc_stmt)).scalar_one_or_none()

    fortnightly_net = 0.0
    if income and income.net_income_fortnightly > 0:
        fortnightly_net = float(income.net_income_fortnightly)
    elif app_obj.draft_data and "net_income" in app_obj.draft_data:
        fortnightly_net = float(app_obj.draft_data["net_income"])

    existing_obligations = 0.0
    if app_obj.draft_data and "existing_obligations" in app_obj.draft_data:
        existing_obligations = float(app_obj.draft_data["existing_obligations"])

    # Evaluate decision engine with dynamic rules from LoanProduct
    decision = CreditDecisionEngine.evaluate(
        product_code=product.code,
        requested_amount=float(app_obj.amount_requested),
        requested_term=app_obj.term_requested,
        compounding_period=app_obj.compounding_period,
        interest_rate_bp=product.interest_rate_bp,
        admin_fee=float(product.admin_fee),
        min_amount=float(product.min_amount),
        max_amount=float(product.max_amount),
        min_income=float(product.min_income),
        max_dti_pct=float(product.max_dti_pct),
        fortnightly_net_income=fortnightly_net,
        existing_fortnightly_obligations=existing_obligations
    )

    # Save decision record
    dec_record = DecisionRecord(
        application_id=app_obj.id,
        customer_id=app_obj.customer_id,
        decision=decision["decision"],
        score=decision["score"],
        dti_ratio=decision["dti_ratio"],
        reason_codes=decision["reason_codes"],
        evaluated_rules=decision["evaluated_rules"]
    )
    db.add(dec_record)

    offer_data = None
    if decision["decision"] in ("APPROVE", "CONDITIONAL_APPROVAL"):
        app_obj.status = "offer_issued"
        payload = OfferService.generate_offer_payload(
            application_id=str(app_obj.id),
            customer_id=str(app_obj.customer_id),
            loan_product_id=str(product.id),
            approved_amount=float(app_obj.amount_requested),
            interest_rate_bp=product.interest_rate_bp,
            term_periods=app_obj.term_requested,
            compounding_period=app_obj.compounding_period
        )
        offer = LoanOffer(
            application_id=app_obj.id,
            customer_id=app_obj.customer_id,
            loan_product_id=product.id,
            approved_amount=payload["approved_amount"],
            interest_rate_bp=payload["interest_rate_bp"],
            term_periods=payload["term_periods"],
            compounding_period=payload["compounding_period"],
            periodic_repayment=payload["periodic_repayment"],
            total_repayment=payload["total_repayment"],
            total_interest=payload["total_interest"],
            fees=payload["fees"],
            expires_at=payload["expires_at"],
            status="issued"
        )
        db.add(offer)
        offer_data = payload
    else:
        app_obj.status = "declined" if decision["decision"] == "DECLINE" else "manual_review"

    from app.services.notification_service import NotificationService
    await NotificationService.notify_application_submitted(
        db=db,
        user_id=current_user.id,
        customer_id=app_obj.customer_id,
        app_id=str(app_obj.id)
    )
    await NotificationService.notify_application_decision(
        db=db,
        user_id=current_user.id,
        customer_id=app_obj.customer_id,
        app_id=str(app_obj.id),
        decision=app_obj.status
    )

    await AuditService.log_event(
        db=db,
        action=f"APPLICATION_SUBMITTED_{app_obj.status.upper()}",
        entity_type="APPLICATION",
        entity_id=str(app_obj.id),
        customer_id=str(app_obj.customer_id),
        payload={"decision": decision["decision"], "summary": decision["summary"]}
    )

    await db.commit()

    return {
        "application_id": str(app_obj.id),
        "status": app_obj.status,
        "decision": decision["decision"],
        "summary": decision["summary"],
        "offer": offer_data
    }
