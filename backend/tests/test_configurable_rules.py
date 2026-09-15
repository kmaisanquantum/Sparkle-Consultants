import pytest
from app.services.credit_decision_engine import CreditDecisionEngine


def test_credit_decision_reads_dynamic_product_rules():
    # Evaluate decision engine with custom product rules (e.g. 2000 BP interest, 100 admin fee, 40% DTI limit)
    res = CreditDecisionEngine.evaluate(
        product_code="DYNAMIC_TEST",
        requested_amount=1000.0,
        requested_term=10,
        compounding_period="fortnightly",
        interest_rate_bp=2000,
        admin_fee=100.0,
        min_amount=100.0,
        max_amount=5000.0,
        min_income=300.0,
        max_dti_pct=40.0,
        fortnightly_net_income=2000.0,
        existing_fortnightly_obligations=100.0
    )

    assert res["decision"] == "APPROVE"
    assert res["dti_ratio"] < 40.0

    # Over DTI limit scenario should decline
    res_dti_exceeded = CreditDecisionEngine.evaluate(
        product_code="DYNAMIC_TEST",
        requested_amount=4000.0,
        requested_term=2,
        compounding_period="fortnightly",
        interest_rate_bp=2000,
        admin_fee=100.0,
        min_amount=100.0,
        max_amount=5000.0,
        min_income=300.0,
        max_dti_pct=40.0,
        fortnightly_net_income=1000.0,
        existing_fortnightly_obligations=350.0
    )
    assert res_dti_exceeded["decision"] == "DECLINE"
