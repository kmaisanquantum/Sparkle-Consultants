from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import uuid

from app.services.calculation_engine import CalculationEngine

class OfferService:
    @staticmethod
    def generate_offer_payload(
        application_id: str,
        customer_id: str,
        loan_product_id: Optional[str],
        approved_amount: float,
        interest_rate_bp: int,
        term_periods: int,
        compounding_period: str,
        admin_fee: float = 50.0,
        validity_days: int = 7
    ) -> Dict[str, Any]:
        calc = CalculationEngine.calculate_loan_summary(
            principal_amount=approved_amount,
            interest_rate_bp=interest_rate_bp,
            compounding_period=compounding_period,
            term_periods=term_periods,
            admin_fee=admin_fee
        )

        expires_at = datetime.now(timezone.utc) + timedelta(days=validity_days)

        return {
            "application_id": application_id,
            "customer_id": customer_id,
            "loan_product_id": loan_product_id,
            "approved_amount": approved_amount,
            "interest_rate_bp": interest_rate_bp,
            "term_periods": term_periods,
            "compounding_period": compounding_period,
            "periodic_repayment": calc["periodic_repayment"],
            "total_repayment": calc["total_repayment"],
            "total_interest": calc["total_interest"],
            "fees": calc["total_fees"],
            "expires_at": expires_at,
            "status": "issued",
            "schedule": calc["schedule"]
        }
