from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import uuid

from app.services.calculation_engine import CalculationEngine
from app.services.pricing_engine import PricingEngine


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
        validity_days: int = 7,
        methodology: str = "reducing_balance",
        risk_band: str = "B"
    ) -> Dict[str, Any]:
        calc = CalculationEngine.calculate_loan_summary(
            principal_amount=approved_amount,
            interest_rate_bp=interest_rate_bp,
            compounding_period=compounding_period,
            term_periods=term_periods,
            admin_fee=admin_fee,
            methodology=methodology
        )

        pricing = PricingEngine.derive_interest_rate(
            amount=approved_amount,
            compounding_period=compounding_period,
            term_periods=term_periods,
            risk_band=risk_band
        )

        expires_at = datetime.now(timezone.utc) + timedelta(days=validity_days)

        calculation_snapshot = {
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
            "methodology": methodology,
            "approved_amount": approved_amount,
            "interest_rate_bp": interest_rate_bp,
            "term_periods": term_periods,
            "compounding_period": compounding_period,
            "admin_fee": admin_fee,
            "pricing_breakdown": pricing,
            "amortisation_schedule": calc["schedule"]
        }

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
            "calculation_methodology": methodology,
            "calculation_snapshot": calculation_snapshot,
            "schedule": calc["schedule"]
        }
