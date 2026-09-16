import pytest
from app.services.calculation_engine import CalculationEngine
from app.services.pricing_engine import PricingEngine
from app.services.topup_service import TopUpService


def test_reducing_balance_amortisation_various_principals():
    for amount in [500.0, 1000.0, 2000.0, 5000.0]:
        summary = CalculationEngine.calculate_loan_summary(
            principal_amount=amount,
            interest_rate_bp=1500,
            compounding_period="fortnightly",
            term_periods=10,
            admin_fee=50.0,
            methodology="reducing_balance"
        )
        assert summary["principal_amount"] == amount
        assert len(summary["schedule"]) == 10
        # Reconcile final closing balance to exactly zero
        assert summary["schedule"][-1]["closing_balance"] == 0.0

        # Reconcile sum of principal and sum of payments
        sum_p = sum(item["principal_due"] for item in summary["schedule"])
        sum_pmt = sum(item["total_due"] for item in summary["schedule"])

        assert round(sum_p, 2) == amount
        assert round(sum_pmt, 2) == round(amount + summary["total_interest"] + summary["total_fees"], 2)


def test_reducing_balance_frequencies():
    for freq in ["weekly", "fortnightly", "monthly"]:
        summary = CalculationEngine.calculate_loan_summary(
            principal_amount=2000.0,
            interest_rate_bp=1200,
            compounding_period=freq,
            term_periods=12,
            admin_fee=30.0
        )
        assert summary["compounding_period"] == freq
        assert summary["schedule"][-1]["closing_balance"] == 0.0


def test_zero_interest_loan():
    summary = CalculationEngine.calculate_loan_summary(
        principal_amount=1000.0,
        interest_rate_bp=0,
        compounding_period="fortnightly",
        term_periods=5,
        admin_fee=0.0
    )
    assert summary["total_interest"] == 0.0
    assert summary["total_repayment"] == 1000.0
    assert summary["periodic_repayment"] == 200.0
    assert summary["schedule"][-1]["closing_balance"] == 0.0


def test_pricing_engine_composition_and_bounds():
    # Test standard composition
    pricing = PricingEngine.derive_interest_rate(
        amount=3000.0,
        compounding_period="fortnightly",
        term_periods=10,
        risk_band="B"
    )
    # Base 400 + Ops 500 + ECL 300 + Margin 300 + Band B 200 = 1700 bp
    assert pricing["effective_annual_rate_bp"] == 1700
    assert pricing["annual_rate_pct"] == 17.0

    # Test ceiling capping at max_rate_bp (3000)
    high_pricing = PricingEngine.derive_interest_rate(
        amount=3000.0,
        compounding_period="fortnightly",
        term_periods=10,
        risk_band="D",
        risk_margin_bp=2000
    )
    assert high_pricing["effective_annual_rate_bp"] == 3000


def test_early_settlement_breakdown():
    settlement = CalculationEngine.calculate_early_settlement(
        outstanding_balance=4000.0,
        accrued_interest=150.0,
        settlement_fee=25.0,
        settlement_rebate_pct=10.0,
        original_principal=5000.0,
        original_total_interest=500.0
    )
    assert settlement["original_principal"] == 5000.0
    assert settlement["repaid_principal"] == 1000.0
    assert settlement["outstanding_principal"] == 4000.0
    assert settlement["accrued_interest"] == 150.0
    assert settlement["settlement_fee"] == 25.0
    assert settlement["rebate_amount"] == 417.5
    assert settlement["net_settlement_amount"] == 3757.5
    assert settlement["interest_saved"] == 350.0


def test_repeat_customer_eligibility():
    eligible = TopUpService.evaluate_repeat_customer_eligibility(
        completed_loans_count=2,
        on_time_repayment_ratio=0.96,
        last_loan_amount=2000.0,
        fortnightly_net_income=3000.0
    )
    assert eligible["pre_qualified"] is True
    assert eligible["assigned_risk_band"] == "A"
    assert eligible["pre_approved_limit"] == 2500.0
