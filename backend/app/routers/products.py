from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_db
from app.models.orm import LoanProduct, User
from app.routers.auth import get_current_user, require_roles
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/v1/products", tags=["products"])


class ProductCreateOrUpdate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    min_amount: float = 100.0
    max_amount: float = 50000.0
    interest_rate_bp: int = 1500
    min_term: int = 2
    max_term: int = 52
    compounding_period: str = "fortnightly"
    admin_fee: float = 50.0
    late_fee_bp: int = 500
    min_income: float = 500.0
    max_dti_pct: float = 50.0
    is_active: bool = True


@router.get("")
async def list_products(db: AsyncSession = Depends(get_db)):
    stmt = select(LoanProduct).where(LoanProduct.is_active == True)
    res = await db.execute(stmt)
    products = res.scalars().all()

    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "description": p.description,
            "min_amount": float(p.min_amount),
            "max_amount": float(p.max_amount),
            "interest_rate_bp": p.interest_rate_bp,
            "min_term": p.min_term,
            "max_term": p.max_term,
            "compounding_period": p.compounding_period,
            "admin_fee": float(p.admin_fee),
            "late_fee_bp": p.late_fee_bp,
            "min_income": float(p.min_income),
            "max_dti_pct": float(p.max_dti_pct),
            "is_active": p.is_active
        }
        for p in products
    ]


@router.get("/admin/all")
async def list_all_products_admin(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin"))
):
    stmt = select(LoanProduct).order_by(LoanProduct.created_at.desc())
    res = await db.execute(stmt)
    products = res.scalars().all()

    return [
        {
            "id": str(p.id),
            "code": p.code,
            "name": p.name,
            "description": p.description,
            "min_amount": float(p.min_amount),
            "max_amount": float(p.max_amount),
            "interest_rate_bp": p.interest_rate_bp,
            "min_term": p.min_term,
            "max_term": p.max_term,
            "compounding_period": p.compounding_period,
            "admin_fee": float(p.admin_fee),
            "late_fee_bp": p.late_fee_bp,
            "min_income": float(p.min_income),
            "max_dti_pct": float(p.max_dti_pct),
            "is_active": p.is_active
        }
        for p in products
    ]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateOrUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin"))
):
    stmt = select(LoanProduct).where(LoanProduct.code == body.code.upper().strip())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"Loan product with code {body.code} already exists.")

    product = LoanProduct(
        code=body.code.upper().strip(),
        name=body.name,
        description=body.description,
        min_amount=body.min_amount,
        max_amount=body.max_amount,
        interest_rate_bp=body.interest_rate_bp,
        min_term=body.min_term,
        max_term=body.max_term,
        compounding_period=body.compounding_period,
        admin_fee=body.admin_fee,
        late_fee_bp=body.late_fee_bp,
        min_income=body.min_income,
        max_dti_pct=body.max_dti_pct,
        is_active=body.is_active
    )
    db.add(product)
    await db.flush()

    await AuditService.log_event(
        db=db,
        action="LOAN_PRODUCT_CREATED",
        entity_type="LOAN_PRODUCT",
        entity_id=str(product.id),
        user_id=str(current_user.id),
        payload={"code": product.code, "name": product.name}
    )

    await db.commit()
    return {"message": "Loan product created successfully", "id": str(product.id)}


@router.put("/{id}")
async def update_product(
    id: str,
    body: ProductCreateOrUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("owner", "admin"))
):
    stmt = select(LoanProduct).where(LoanProduct.id == uuid.UUID(id))
    product = (await db.execute(stmt)).scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Loan product not found")

    product.code = body.code.upper().strip()
    product.name = body.name
    product.description = body.description
    product.min_amount = body.min_amount
    product.max_amount = body.max_amount
    product.interest_rate_bp = body.interest_rate_bp
    product.min_term = body.min_term
    product.max_term = body.max_term
    product.compounding_period = body.compounding_period
    product.admin_fee = body.admin_fee
    product.late_fee_bp = body.late_fee_bp
    product.min_income = body.min_income
    product.max_dti_pct = body.max_dti_pct
    product.is_active = body.is_active

    await AuditService.log_event(
        db=db,
        action="LOAN_PRODUCT_UPDATED",
        entity_type="LOAN_PRODUCT",
        entity_id=str(product.id),
        user_id=str(current_user.id),
        payload={"code": product.code, "name": product.name}
    )

    await db.commit()
    return {"message": "Loan product updated successfully", "id": str(product.id)}
