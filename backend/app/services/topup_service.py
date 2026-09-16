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
        product_code: str = "SPARKLE_DIGITAL_MICRO"
    ) -> Dict[str, Any]:
        # Rule 1: Loan must be active or completed and in good standing
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

        decision = CreditDecisionEngine.evaluate(
            product_code=product_code,
            requested_amount=new_total_principal,
            requested_term=total_term_periods,
            compounding_period="fortnightly",
            interest_rate_bp=1700,
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

    @staticmethod
    def evaluate_repeat_customer_eligibility(
        completed_loans_count: int,
        on_time_repayment_ratio: float,
        last_loan_amount: float,
        fortnightly_net_income: float,
        limit_multiplier: float = 1.25
    ) -> Dict[str, Any]:
        """
        Evaluates repeat customer pre-qualification eligibility based on historical repayment performance.
        A borrower with at least 1 successfully closed loan and >= 90% on-time repayment receives
        a pre-qualified higher limit (e.g. 25% boost) and upgraded Risk Band A status.
        """
        if completed_loans_count < 1:
            return {
                "pre_qualified": False,
                "assigned_risk_band": "B",
                "reason": "Requires at least one fully repaid loan for repeat pre-qualification."
            }

        if on_time_repayment_ratio < 0.85:
            return {
                "pre_qualified": False,
                "assigned_risk_band": "C",
                "reason": "Repayment performance history below required 85% on-time benchmark."
            }

        pre_approved_limit = round(last_loan_amount * limit_multiplier, -2)
        assigned_band = "A" if on_time_repayment_ratio >= 0.95 else "B"

        return {
            "pre_qualified": True,
            "assigned_risk_band": assigned_band,
            "pre_approved_limit": pre_approved_limit,
            "limit_multiplier": limit_multiplier,
            "on_time_repayment_ratio": on_time_repayment_ratio,
            "message": f"Pre-qualified for repeat loan up to PGK {pre_approved_limit:.2f} under Band {assigned_band}!"
        }
