from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.calculation_engine import CalculationEngine

router = APIRouter(prefix="/api/v1/calculator", tags=["calculator"])


class CalculationRequest(BaseModel):
    principal_amount: float = Field(..., gt=0, description="Requested principal amount in PGK")
    interest_rate_bp: int = Field(1500, ge=0, description="Interest rate in basis points per period")
    compounding_period: str = Field("fortnightly", description="weekly, fortnightly, monthly")
    term_periods: int = Field(..., gt=0, description="Total repayment periods")
    admin_fee: float = Field(50.0, ge=0, description="One-off processing admin fee")


class EarlySettlementRequest(BaseModel):
    outstanding_balance: float
    accrued_interest: float = 0.0
    settlement_rebate_pct: float = 0.0


@router.post("")
async def calculate_repayments(body: CalculationRequest):
    try:
        summary = CalculationEngine.calculate_loan_summary(
            principal_amount=body.principal_amount,
            interest_rate_bp=body.interest_rate_bp,
            compounding_period=body.compounding_period,
            term_periods=body.term_periods,
            admin_fee=body.admin_fee
        )
        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/early-settlement")
async def calculate_early_settlement(body: EarlySettlementRequest):
    return CalculationEngine.calculate_early_settlement(
        outstanding_balance=body.outstanding_balance,
        accrued_interest=body.accrued_interest,
        settlement_rebate_pct=body.settlement_rebate_pct
    )
