from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.calculation_engine import CalculationEngine
from app.services.pricing_engine import PricingEngine
from app.models.orm import LoanProduct, SystemSetting

router = APIRouter(prefix="/api/v1/calculator", tags=["calculator"])


class CalculationRequest(BaseModel):
    principal_amount: float = Field(..., gt=0, description="Requested principal amount in PGK")
    interest_rate_bp: Optional[int] = Field(None, description="Interest rate in basis points per period (derived if None)")
    compounding_period: str = Field("fortnightly", description="weekly, fortnightly, monthly")
    term_periods: int = Field(..., gt=0, description="Total repayment periods")
    admin_fee: float = Field(50.0, ge=0, description="One-off processing admin fee")
    risk_band: str = Field("B", description="A, B, C, or D")
    methodology: str = Field("reducing_balance", description="reducing_balance or flat")


class AffordabilityRequest(BaseModel):
    fortnightly_income: float = Field(..., gt=0, description="Verified or declared fortnightly net income in PGK")
    existing_fortnightly_obligations: float = Field(0.0, ge=0, description="Existing recurring debt obligations")
    max_dti_pct: float = Field(50.0, ge=0, le=100, description="Maximum permitted Debt-To-Income percentage")
    compounding_period: str = Field("fortnightly", description="weekly, fortnightly, monthly")
    desired_term_periods: int = Field(10, gt=0)
    risk_band: str = Field("B")


class WhatIfComparisonRequest(BaseModel):
    principal_amount: float = Field(..., gt=0)
    compounding_period: str = Field("fortnightly")
    risk_band: str = Field("B")
    terms: List[int] = Field(default_factory=lambda: [4, 8, 12, 26])


class EarlySettlementRequest(BaseModel):
    outstanding_balance: float
    accrued_interest: float = 0.0
    settlement_fee: float = 0.0
    settlement_rebate_pct: float = 0.0
    original_principal: Optional[float] = None
    original_total_interest: Optional[float] = None


@router.post("")
async def calculate_repayments(
    body: CalculationRequest,
    db: AsyncSession = Depends(get_db)
):
    try:
        rate_bp = body.interest_rate_bp
        if rate_bp is None:
            prod_stmt = select(LoanProduct).where(LoanProduct.is_active == True).limit(1)
            prod = (await db.execute(prod_stmt)).scalar_one_or_none()
            rate_bp = prod.interest_rate_bp if prod else 1500

        pricing = PricingEngine.derive_interest_rate(
            amount=body.principal_amount,
            compounding_period=body.compounding_period,
            term_periods=body.term_periods,
            risk_band=body.risk_band
        )

        effective_rate_bp = pricing["effective_annual_rate_bp"]

        summary = CalculationEngine.calculate_loan_summary(
            principal_amount=body.principal_amount,
            interest_rate_bp=effective_rate_bp,
            compounding_period=body.compounding_period,
            term_periods=body.term_periods,
            admin_fee=body.admin_fee,
            methodology=body.methodology
        )

        summary["pricing_breakdown"] = pricing
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/affordability")
async def calculate_affordability(
    body: AffordabilityRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Computes maximum affordable loan repayment and back-calculates
    maximum principal borrowable based on income, obligations, and configurable DTI.
    """
    period = body.compounding_period.lower()
    if period == "weekly":
        inc_multiplier = 0.5
    elif period == "monthly":
        inc_multiplier = 2.1667
    else:
        inc_multiplier = 1.0

    net_income = body.fortnightly_income * inc_multiplier
    obligations = body.existing_fortnightly_obligations * inc_multiplier

    max_allowed_debt = net_income * (body.max_dti_pct / 100.0)
    max_repayment_capacity = max(0.0, max_allowed_debt - obligations)

    pricing = PricingEngine.derive_interest_rate(
        amount=5000.0,
        compounding_period=body.compounding_period,
        term_periods=body.desired_term_periods,
        risk_band=body.risk_band
    )
    rate_bp = pricing["effective_annual_rate_bp"]

    # Binary search or iterative estimation to find max principal where periodic_repayment <= max_repayment_capacity
    low_p, high_p = 100.0, 100000.0
    best_p = 100.0

    while high_p - low_p > 1.0:
        mid_p = (low_p + high_p) / 2.0
        calc = CalculationEngine.calculate_loan_summary(
            principal_amount=mid_p,
            interest_rate_bp=rate_bp,
            compounding_period=body.compounding_period,
            term_periods=body.desired_term_periods
        )
        if calc["periodic_repayment"] <= max_repayment_capacity:
            best_p = mid_p
            low_p = mid_p
        else:
            high_p = mid_p

    final_calc = CalculationEngine.calculate_loan_summary(
        principal_amount=round(best_p, -1),  # Round to nearest 10 PGK
        interest_rate_bp=rate_bp,
        compounding_period=body.compounding_period,
        term_periods=body.desired_term_periods
    )

    return {
        "fortnightly_net_income": body.fortnightly_income,
        "max_dti_pct": body.max_dti_pct,
        "max_repayment_capacity": round(max_repayment_capacity, 2),
        "estimated_max_loan": round(best_p, -1),
        "compounding_period": body.compounding_period,
        "term_periods": body.desired_term_periods,
        "recommended_summary": final_calc
    }


@router.post("/what-if")
async def calculate_what_if(body: WhatIfComparisonRequest):
    """
    Compares loan terms and total cost for a fixed principal across multiple terms.
    """
    pricing = PricingEngine.derive_interest_rate(
        amount=body.principal_amount,
        compounding_period=body.compounding_period,
        term_periods=10,
        risk_band=body.risk_band
    )
    rate_bp = pricing["effective_annual_rate_bp"]

    comparisons = []
    for term in body.terms:
        if term <= 0:
            continue
        calc = CalculationEngine.calculate_loan_summary(
            principal_amount=body.principal_amount,
            interest_rate_bp=rate_bp,
            compounding_period=body.compounding_period,
            term_periods=term
        )
        comparisons.append({
            "term_periods": term,
            "periodic_repayment": calc["periodic_repayment"],
            "total_interest": calc["total_interest"],
            "total_repayment": calc["total_repayment"]
        })

    return {
        "principal_amount": body.principal_amount,
        "compounding_period": body.compounding_period,
        "effective_rate_bp": rate_bp,
        "comparisons": comparisons
    }


@router.post("/early-settlement")
async def calculate_early_settlement(body: EarlySettlementRequest):
    return CalculationEngine.calculate_early_settlement(
        outstanding_balance=body.outstanding_balance,
        accrued_interest=body.accrued_interest,
        settlement_fee=body.settlement_fee,
        settlement_rebate_pct=body.settlement_rebate_pct,
        original_principal=body.original_principal,
        original_total_interest=body.original_total_interest
    )
