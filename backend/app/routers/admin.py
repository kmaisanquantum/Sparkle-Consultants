from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List

from app.core.database import get_db
from app.routers.auth import get_current_user, require_roles
from app.models.orm import (
    Customer, Loan, LoanApplication, Transaction, Payment, Collection,
    LoanProduct, AuditLog, Complaint, SystemSetting, User, RiskProfile
)
from app.core.crypto import decrypt_field
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class UpdateSystemSettingRequest(BaseModel):
    value: str
    description: Optional[str] = None
    category: Optional[str] = "general"


@router.get("/metrics")
async def get_admin_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "underwriter", "compliance_officer"))
):
    total_customers = (await db.execute(select(func.count(Customer.id)))).scalar() or 0
    total_active_loans = (await db.execute(select(func.count(Loan.id)).where(Loan.status == "active"))).scalar() or 0
    total_capital_out = (await db.execute(select(func.sum(Loan.outstanding_balance)).where(Loan.status == "active"))).scalar() or 0.0

    approved_apps = (await db.execute(select(func.count(LoanApplication.id)).where(LoanApplication.status.in_(["offer_issued", "offer_accepted", "disbursed", "completed"])))).scalar() or 0
    rejected_apps = (await db.execute(select(func.count(LoanApplication.id)).where(LoanApplication.status == "declined"))).scalar() or 0
    pending_apps = (await db.execute(select(func.count(LoanApplication.id)).where(LoanApplication.status.in_(["submitted", "manual_review"])))).scalar() or 0

    disbursed_totals = (await db.execute(select(func.sum(Transaction.amount)).where(Transaction.type == "disbursement"))).scalar() or 0.0
    repayments_received = (await db.execute(select(func.sum(Transaction.amount)).where(Transaction.type == "repayment"))).scalar() or 0.0
    outstanding_balances = (await db.execute(select(func.sum(Loan.outstanding_balance)).where(Loan.status.in_(["active", "overdue"])))).scalar() or 0.0

    overdue_count = (await db.execute(select(func.count(Collection.id)).where(Collection.status == "open"))).scalar() or 0

    # Arrears breakdown buckets
    bucket_1_7 = (await db.execute(select(func.count(Collection.id)).where(Collection.stage == "overdue_1_7"))).scalar() or 0
    bucket_8_30 = (await db.execute(select(func.count(Collection.id)).where(Collection.stage == "overdue_8_30"))).scalar() or 0
    bucket_31_60 = (await db.execute(select(func.count(Collection.id)).where(Collection.stage == "overdue_31_60"))).scalar() or 0
    bucket_60_plus = (await db.execute(select(func.count(Collection.id)).where(Collection.stage.in_(["overdue_61_90", "serious_arrears", "default", "recovery"])))).scalar() or 0

    return {
        "tenant_name": "Sparkle Consultants",
        "total_customers": total_customers,
        "active_loans": total_active_loans,
        "total_capital_out": float(total_capital_out),
        "approved_applications": approved_apps,
        "rejected_applications": rejected_apps,
        "pending_applications": pending_apps,
        "disbursed_totals": float(disbursed_totals),
        "repayments_received": float(repayments_received),
        "outstanding_balances": float(outstanding_balances),
        "overdue_collections": overdue_count,
        "arrears_buckets": {
            "1_7_days": bucket_1_7,
            "8_30_days": bucket_8_30,
            "31_60_days": bucket_31_60,
            "60_plus_days": bucket_60_plus
        }
    }


@router.get("/customers")
async def list_admin_customers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "underwriter", "compliance_officer", "collections_agent"))
):
    stmt = select(Customer).limit(50)
    res = await db.execute(stmt)
    customers = res.scalars().all()

    out = []
    for c in customers:
        full_name = decrypt_field(c.encrypted_full_name) if c.encrypted_full_name else "Customer"
        out.append({
            "id": str(c.id),
            "full_name": full_name,
            "is_public_servant": c.is_public_servant,
            "status": c.status,
            "risk_flag": c.risk_flag,
            "created_at": c.created_at
        })
    return out


@router.get("/applications")
async def list_admin_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "underwriter", "compliance_officer"))
):
    stmt = select(LoanApplication).order_by(LoanApplication.created_at.desc()).limit(50)
    res = await db.execute(stmt)
    apps = res.scalars().all()

    return [
        {
            "id": str(a.id),
            "customer_id": str(a.customer_id),
            "amount_requested": float(a.amount_requested),
            "term_requested": a.term_requested,
            "compounding_period": a.compounding_period,
            "purpose": a.purpose,
            "status": a.status,
            "created_at": a.created_at
        }
        for a in apps
    ]


@router.get("/collections")
async def list_admin_collections(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "collections_agent", "underwriter", "compliance_officer"))
):
    stmt = select(Collection).order_by(Collection.days_overdue.desc()).limit(50)
    res = await db.execute(stmt)
    cols = res.scalars().all()

    return [
        {
            "id": str(c.id),
            "loan_id": str(c.loan_id),
            "customer_id": str(c.customer_id),
            "stage": c.stage,
            "days_overdue": c.days_overdue,
            "amount_overdue": float(c.amount_overdue),
            "notes": c.notes,
            "status": c.status
        }
        for c in cols
    ]


@router.get("/audit-logs")
async def list_admin_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "compliance_officer"))
):
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        {
            "id": str(l.id),
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "user_id": str(l.user_id) if l.user_id else None,
            "customer_id": str(l.customer_id) if l.customer_id else None,
            "payload": l.payload,
            "timestamp": l.timestamp
        }
        for l in logs
    ]


@router.get("/settings")
async def list_admin_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin", "compliance_officer"))
):
    stmt = select(SystemSetting)
    res = await db.execute(stmt)
    settings = res.scalars().all()

    return [
        {
            "id": str(s.id),
            "key": s.key,
            "value": s.value,
            "description": s.description,
            "category": s.category
        }
        for s in settings
    ]


@router.put("/settings/{key}")
async def update_admin_setting(
    key: str,
    body: UpdateSystemSettingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin"))
):
    stmt = select(SystemSetting).where(SystemSetting.key == key)
    setting = (await db.execute(stmt)).scalar_one_or_none()

    if not setting:
        setting = SystemSetting(
            key=key,
            value=body.value,
            description=body.description,
            category=body.category or "general"
        )
        db.add(setting)
    else:
        setting.value = body.value
        if body.description:
            setting.description = body.description
        if body.category:
            setting.category = body.category

    await AuditService.log_event(
        db=db,
        action="SYSTEM_SETTING_UPDATED",
        entity_type="SYSTEM_SETTING",
        entity_id=key,
        user_id=str(current_user.id),
        payload={"key": key, "value": body.value}
    )

    await db.commit()
    return {"message": f"System setting '{key}' updated successfully", "key": key, "value": body.value}
