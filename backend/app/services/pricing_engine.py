from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional

# Default risk bands (editable via SystemSetting or admin API)
DEFAULT_RISK_BANDS = {
    "A": {"name": "Low Risk / Public Servant", "rate_adjustment_bp": 0, "max_loan": 50000.0, "max_term": 52},
    "B": {"name": "Standard Working Citizen", "rate_adjustment_bp": 200, "max_loan": 20000.0, "max_term": 26},
    "C": {"name": "Watchlist / Higher Risk", "rate_adjustment_bp": 500, "max_loan": 5000.0, "max_term": 12},
    "D": {"name": "Sub-Prime / Manual Review Only", "rate_adjustment_bp": 1000, "max_loan": 2000.0, "max_term": 6}
}


class PricingEngine:
    """
    Sparkle Pricing Engine.
    Composes annual interest rate from configurable components:
      Annual Rate (BP) = Base Funding Cost + Operating Cost + ECL + Risk Margin + Risk Band Adjustment
    Bounded by min_rate_bp and max_rate_bp.
    Derives periodic interest rate based on frequency.
    """

    @staticmethod
    def derive_interest_rate(
        amount: float,
        compounding_period: str,
        term_periods: int,
        risk_band: str = "B",
        base_funding_cost_bp: int = 400,     # 4.0%
        operating_cost_bp: int = 500,        # 5.0%
        expected_credit_loss_bp: int = 300,  # 3.0%
        risk_margin_bp: int = 300,           # 3.0%
        min_rate_bp: int = 1000,             # 10.0%
        max_rate_bp: int = 3000,             # 30.0%
        custom_risk_bands: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        bands = custom_risk_bands or DEFAULT_RISK_BANDS
        band_info = bands.get(risk_band.upper(), bands.get("B"))

        band_adjustment_bp = band_info.get("rate_adjustment_bp", 0)

        # Raw calculated annual rate
        unbounded_rate_bp = (
            base_funding_cost_bp
            + operating_cost_bp
            + expected_credit_loss_bp
            + risk_margin_bp
            + band_adjustment_bp
        )

        # Apply min/max bounds
        effective_annual_rate_bp = max(min_rate_bp, min(max_rate_bp, unbounded_rate_bp))

        period = compounding_period.lower().strip()
        if period == "weekly":
            periods_per_year = 52
        elif period == "monthly":
            periods_per_year = 12
        else:
            period = "fortnightly"
            periods_per_year = 26

        annual_rate_pct = float(Decimal(effective_annual_rate_bp) / Decimal("100"))
        periodic_rate_pct = float(
            (Decimal(effective_annual_rate_bp) / Decimal("100") / Decimal(periods_per_year)).quantize(
                Decimal("0.0001"), rounding=ROUND_HALF_UP
            )
        )

        return {
            "effective_annual_rate_bp": effective_annual_rate_bp,
            "annual_rate_pct": annual_rate_pct,
            "periodic_rate_pct": periodic_rate_pct,
            "compounding_period": period,
            "periods_per_year": periods_per_year,
            "risk_band": risk_band.upper(),
            "risk_band_info": band_info,
            "breakdown": {
                "base_funding_cost_bp": base_funding_cost_bp,
                "operating_cost_bp": operating_cost_bp,
                "expected_credit_loss_bp": expected_credit_loss_bp,
                "risk_margin_bp": risk_margin_bp,
                "risk_band_adjustment_bp": band_adjustment_bp,
                "unbounded_rate_bp": unbounded_rate_bp,
                "min_rate_bp": min_rate_bp,
                "max_rate_bp": max_rate_bp
            }
        }
