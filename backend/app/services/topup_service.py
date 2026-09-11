from typing import Dict, Any, Optional
from app.services.credit_decision_engine import CreditDecisionEngine

class TopUpService:
    @staticmethod
    def evaluate_topup_eligibility(
        current_loan_status: str,
        current_outstanding_balance: float,
        original_principal: float,
        completed_instalments_count: int,
        total_term_periods: int,
        requested_additional_amount: float,
        fortnightly_net_income: float,
        product_code: str = "PERSONAL_STANDARD"
    ) -> Dict[str, Any]:
        # Rule 1: Loan must be active and in good standing
        if current_loan_status not in ("active", "completed"):
            return {
                "eligible": False,
                "reason": f"Top-up unavailable for loans with status '{current_loan_status}'."
            }

        # Rule 2: At least 30% or 3 instalments repaid
        if completed_instalments_count < 3 and (current_outstanding_balance / original_principal) > 0.70:
            return {
                "eligible": False,
                "reason": "Top-up requires at least 3 completed instalments or 30% principal reduction."
            }

        new_total_principal = current_outstanding_balance + requested_additional_amount

        # Evaluate decision engine for consolidated amount
        decision = CreditDecisionEngine.evaluate(
            product_code=product_code,
            requested_amount=new_total_principal,
            requested_term=total_term_periods,
            compounding_period="fortnightly",
            interest_rate_bp=1500,
            admin_fee=50.0,
            min_amount=200,
            max_amount=50000,
            min_income=300,
            max_dti_pct=50.0,
            fortnightly_net_income=fortnightly_net_income,
            existing_fortnightly_obligations=0.0
        )

        return {
            "eligible": decision["decision"] in ("APPROVE", "CONDITIONAL_APPROVAL"),
            "decision": decision["decision"],
            "new_total_principal": new_total_principal,
            "additional_amount": requested_additional_amount,
            "decision_summary": decision["summary"]
        }
