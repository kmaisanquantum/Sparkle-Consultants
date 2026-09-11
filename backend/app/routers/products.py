from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.orm import LoanProduct

router = APIRouter(prefix="/api/v1/products", tags=["products"])


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
            "min_income": float(p.min_income),
            "max_dti_pct": float(p.max_dti_pct)
        }
        for p in products
    ]
