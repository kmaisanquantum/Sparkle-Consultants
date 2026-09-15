import uuid
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.crypto import hash_password, decrypt_field
from app.routers.auth import get_current_user, require_roles
from app.models.orm import (
    Customer, Loan, LoanApplication, Transaction, Payment, Collection,
    LoanProduct, AuditLog, Complaint, SystemSetting, User, RiskProfile, Tenant
)
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class UpdateSystemSettingRequest(BaseModel):
    value: str
    description: Optional[str] = None
    category: Optional[str] = "general"


class UserCreateRequest(BaseModel):
    email: EmailStr
    password: str
    role: str # administrator, admin, owner, customer, client, underwriter, collections_agent, compliance_officer
    full_name: str


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserOutResponse(BaseModel):
    id: str
    email: str
    role: str
    full_name: str
    is_active: bool
    created_at: Any


@router.get("/metrics")
async def get_admin_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("administrator", "owner", "admin", "underwriter", "compliance_officer"))
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


# ==========================================
# ADMIN USER MANAGEMENT API (CRUD)
# ==========================================

@router.get("/users", response_model=List[UserOutResponse])
async def list_admin_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("administrator", "admin", "owner"))
):
    stmt = select(User).order_by(User.created_at.desc())
    res = await db.execute(stmt)
    users = res.scalars().all()

    return [
        UserOutResponse(
            id=str(u.id),
            email=u.email,
            role=u.role,
            full_name=u.full_name,
            is_active=u.is_active,
            created_at=u.created_at
        )
        for u in users
    ]


@router.post("/users", response_model=UserOutResponse, status_code=status.HTTP_201_CREATED)
async def create_admin_user(
    body: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("administrator", "admin", "owner"))
):
    # Check if email exists
    stmt = select(User).where(User.email == body.email.lower().strip())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"An account with email {body.email} already exists."
        )

    # Get primary tenant
    tenant_stmt = select(Tenant).limit(1)
    tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()
    tenant_id = tenant.id if tenant else None

    user = User(
        tenant_id=tenant_id,
        email=body.email.lower().strip(),
        password_hash=hash_password(body.password),
        role=body.role.lower().strip(),
        full_name=body.full_name,
        is_active=True
    )
    db.add(user)
    await db.flush()

    await AuditService.log_event(
        db=db,
        action="ADMIN_CREATE_USER",
        entity_type="USER",
        entity_id=str(user.id),
        user_id=str(current_user.id),
        payload={"created_user_id": str(user.id), "email": user.email, "role": user.role}
    )

    await db.commit()
    await db.refresh(user)

    return UserOutResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at
    )


@router.patch("/users/{user_id}", response_model=UserOutResponse)
@router.put("/users/{user_id}", response_model=UserOutResponse)
async def update_admin_user(
    user_id: str,
    body: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("administrator", "admin", "owner"))
):
    stmt = select(User).where(User.id == uuid.UUID(user_id))
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent demoting or deactivating self
    if user.id == current_user.id:
        if body.is_active is False:
            raise HTTPException(status_code=400, detail="Cannot deactivate your own administrator account.")
        if body.role and body.role not in ("administrator", "admin", "owner"):
            raise HTTPException(status_code=400, detail="Cannot demote your own administrator role.")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role.lower().strip()
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None and body.password.strip():
        user.password_hash = hash_password(body.password.strip())

    await AuditService.log_event(
        db=db,
        action="ADMIN_UPDATE_USER",
        entity_type="USER",
        entity_id=str(user.id),
        user_id=str(current_user.id),
        payload={"updated_user_id": str(user.id), "role": user.role, "is_active": user.is_active}
    )

    await db.commit()
    await db.refresh(user)

    return UserOutResponse(
        id=str(user.id),
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        is_active=user.is_active,
        created_at=user.created_at
    )


@router.delete("/users/{user_id}")
async def delete_admin_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("administrator", "admin", "owner"))
):
    target_uuid = uuid.UUID(user_id)
    if target_uuid == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete or deactivate your own account.")

    stmt = select(User).where(User.id == target_uuid)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Ensure not deleting the last remaining administrator
    if user.role in ("administrator", "admin", "owner") and user.is_active:
        admin_count_stmt = select(func.count(User.id)).where(
            User.role.in_(["administrator", "admin", "owner"]),
            User.is_active == True
        )
        admin_count = (await db.execute(admin_count_stmt)).scalar() or 0
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot delete or deactivate the last remaining administrator.")

    # Soft delete via deactivation to preserve financial/audit history
    user.is_active = False

    await AuditService.log_event(
        db=db,
        action="ADMIN_DEACTIVATE_USER",
        entity_type="USER",
        entity_id=str(user.id),
        user_id=str(current_user.id),
        payload={"deactivated_user_id": str(user.id), "email": user.email}
    )

    await db.commit()
    return {"message": f"User {user.email} has been deactivated successfully.", "id": str(user.id)}


@router.get("/customers")
async def list_admin_customers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("administrator", "owner", "admin", "underwriter", "compliance_officer", "collections_agent"))
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
    current_user: User = Depends(require_roles("administrator", "owner", "admin", "underwriter", "compliance_officer"))
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
    current_user: User = Depends(require_roles("administrator", "owner", "admin", "collections_agent", "underwriter", "compliance_officer"))
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
    current_user: User = Depends(require_roles("administrator", "owner", "admin", "compliance_officer"))
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
    current_user: User = Depends(require_roles("administrator", "owner", "admin", "compliance_officer"))
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
    current_user: User = Depends(require_roles("administrator", "owner", "admin"))
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
