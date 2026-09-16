import pytest
import asyncio
from datetime import date
from app.services.calculation_engine import CalculationEngine
from app.services.credit_decision_engine import CreditDecisionEngine
from app.services.collections_service import CollectionsService
from app.services.payments.bsp_provider import BSPPaymentProvider

def test_calculation_engine_loan_summary():
    # Test flat methodology explicitly
    calc_flat = CalculationEngine.calculate_loan_summary(
        principal_amount=10000.0,
        interest_rate_bp=1500, # 15%
        compounding_period="fortnightly",
        term_periods=10,
        admin_fee=50.0,
        methodology="flat"
    )
    assert calc_flat["principal_amount"] == 10000.0
    assert calc_flat["total_interest"] == 1500.0
    assert calc_flat["total_fees"] == 50.0
    assert calc_flat["total_repayment"] == 11550.0
    assert calc_flat["periodic_repayment"] == 1155.0
    assert len(calc_flat["schedule"]) == 10

    # Test default reducing-balance annuity methodology
    calc_rb = CalculationEngine.calculate_loan_summary(
        principal_amount=10000.0,
        interest_rate_bp=1500,
        compounding_period="fortnightly",
        term_periods=10,
        admin_fee=50.0
    )
    assert calc_rb["principal_amount"] == 10000.0
    assert calc_rb["total_interest"] == 320.05
    assert calc_rb["schedule"][-1]["closing_balance"] == 0.0

def test_calculation_engine_early_settlement():
    settlement = CalculationEngine.calculate_early_settlement(
        outstanding_balance=5000.0,
        accrued_interest=200.0,
        settlement_rebate_pct=10.0
    )
    assert settlement["outstanding_principal"] == 5000.0
    assert settlement["accrued_interest"] == 200.0
    assert settlement["rebate_amount"] == 520.0
    assert settlement["net_settlement_amount"] == 4680.0

def test_credit_decision_engine_approve():
    res = CreditDecisionEngine.evaluate(
        product_code="PERSONAL_STANDARD",
        requested_amount=2000.0,
        requested_term=10,
        compounding_period="fortnightly",
        interest_rate_bp=1500,
        admin_fee=50.0,
        min_amount=200,
        max_amount=50000,
        min_income=500,
        max_dti_pct=50.0,
        fortnightly_net_income=2000.0,
        existing_fortnightly_obligations=100.0
    )
    assert res["decision"] in ("APPROVE", "CONDITIONAL_APPROVAL")
    assert res["dti_ratio"] < 50.0

def test_credit_decision_engine_decline_active_default():
    res = CreditDecisionEngine.evaluate(
        product_code="PERSONAL_STANDARD",
        requested_amount=2000.0,
        requested_term=10,
        compounding_period="fortnightly",
        interest_rate_bp=1500,
        admin_fee=50.0,
        min_amount=200,
        max_amount=50000,
        min_income=500,
        max_dti_pct=50.0,
        fortnightly_net_income=2000.0,
        active_defaults_count=1
    )
    assert res["decision"] == "DECLINE"
    assert "DECLINE_ACTIVE_DEFAULT_EXISTS" in res["reason_codes"]

def test_collections_stages():
    stage_current = CollectionsService.determine_stage(0)
    assert stage_current == "current"

    stage_due_today = CollectionsService.determine_stage(1)
    assert stage_due_today == "due_today"

    stage_overdue_7 = CollectionsService.determine_stage(5)
    assert stage_overdue_7 == "overdue_1_7"

    stage_default = CollectionsService.determine_stage(150)
    assert stage_default == "default"

@pytest.mark.asyncio
async def test_bsp_provider_stub():
    provider = BSPPaymentProvider()
    col = await provider.initiate_collection(
        amount=500.0,
        currency="PGK",
        customer_reference="CUST-100",
        idempotency_key="IDEM-100"
    )
    assert col["status"] == "successful"
    assert col["provider"] == "bsp"
