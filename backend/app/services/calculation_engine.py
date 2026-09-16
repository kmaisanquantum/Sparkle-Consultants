from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Any, Optional


def _quantize_money(amount: Decimal) -> Decimal:
    """Quantize decimal currency value to 2 decimal places using ROUND_HALF_UP."""
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class CalculationEngine:
    """
    Authoritative server-side financial calculation engine using exact Decimal math.
    Primary methodology: Reducing-balance annuity amortisation.
    Flat methodology retained as fallback option when methodology == 'flat'.
    """

    @staticmethod
    def calculate_loan_summary(
        principal_amount: float,
        interest_rate_bp: int,
        compounding_period: str,
        term_periods: int,
        admin_fee: float = 0.0,
        start_date: Optional[date] = None,
        methodology: str = "reducing_balance"
    ) -> Dict[str, Any]:
        if principal_amount <= 0:
            raise ValueError("Principal amount must be greater than zero")
        if term_periods <= 0:
            raise ValueError("Term periods must be greater than zero")

        P = _quantize_money(Decimal(str(principal_amount)))
        fee = _quantize_money(Decimal(str(admin_fee)))
        method = methodology.lower().strip() if methodology else "reducing_balance"
        period = compounding_period.lower().strip()

        if period == "weekly":
            days_per_period = 7
            periods_per_year = Decimal("52")
        elif period == "monthly":
            days_per_period = 30
            periods_per_year = Decimal("12")
        else:  # fortnightly
            period = "fortnightly"
            days_per_period = 14
            periods_per_year = Decimal("26")

        start = start_date or date.today()
        due_date = start + timedelta(days=days_per_period * term_periods)

        # Annual interest rate decimal (e.g. 1500 bp -> 0.15)
        annual_rate = Decimal(interest_rate_bp) / Decimal("10000")
        periodic_rate = annual_rate / periods_per_year

        n = term_periods
        schedule: List[Dict[str, Any]] = []

        if method == "flat":
            # Flat interest calculation
            total_interest = _quantize_money(P * annual_rate)
            total_fees = fee
            total_repayment = P + total_interest + total_fees
            periodic_repayment = _quantize_money(total_repayment / Decimal(n))

            principal_per_period = _quantize_money(P / Decimal(n))
            interest_per_period = _quantize_money(total_interest / Decimal(n))
            fee_per_period = _quantize_money(total_fees / Decimal(n))

            acc_p = Decimal("0.00")
            acc_i = Decimal("0.00")
            acc_f = Decimal("0.00")

            for i in range(1, n + 1):
                inst_date = start + timedelta(days=days_per_period * i)
                if i == n:
                    p_due = P - acc_p
                    i_due = total_interest - acc_i
                    f_due = total_fees - acc_f
                else:
                    p_due = principal_per_period
                    i_due = interest_per_period
                    f_due = fee_per_period
                    acc_p += p_due
                    acc_i += i_due
                    acc_f += f_due

                schedule.append({
                    "instalment_number": i,
                    "due_date": inst_date.isoformat(),
                    "opening_balance": float(_quantize_money(P - (acc_p - p_due if i > 1 else Decimal("0.00")))),
                    "principal_due": float(p_due),
                    "interest_due": float(i_due),
                    "fee_due": float(f_due),
                    "total_due": float(p_due + i_due + f_due),
                    "closing_balance": float(_quantize_money(max(Decimal("0.00"), P - acc_p)))
                })
        else:
            # Reducing balance amortisation using annuity formula
            # PMT = P * [ r * (1+r)^n ] / [ (1+r)^n - 1 ]
            if periodic_rate == Decimal("0"):
                pmt_principal = _quantize_money(P / Decimal(n))
            else:
                one_plus_r = Decimal("1") + periodic_rate
                factor = one_plus_r ** n
                pmt_decimal = P * (periodic_rate * factor) / (factor - Decimal("1"))
                pmt_principal = _quantize_money(pmt_decimal)

            fee_per_period = _quantize_money(fee / Decimal(n))
            fee_last = fee - (fee_per_period * Decimal(n - 1))

            opening_balance = P
            total_interest = Decimal("0.00")
            total_fees = fee

            for i in range(1, n + 1):
                inst_date = start + timedelta(days=days_per_period * i)
                interest_due = _quantize_money(opening_balance * periodic_rate)
                f_due = fee_last if i == n else fee_per_period

                if i == n:
                    # Final payment reconciles closing balance to exactly zero
                    principal_due = opening_balance
                    closing_balance = Decimal("0.00")
                else:
                    principal_due = _quantize_money(pmt_principal - interest_due)
                    if principal_due > opening_balance:
                        principal_due = opening_balance
                    closing_balance = opening_balance - principal_due

                total_due = principal_due + interest_due + f_due
                total_interest += interest_due

                schedule.append({
                    "instalment_number": i,
                    "due_date": inst_date.isoformat(),
                    "opening_balance": float(opening_balance),
                    "principal_due": float(principal_due),
                    "interest_due": float(interest_due),
                    "fee_due": float(f_due),
                    "total_due": float(total_due),
                    "closing_balance": float(closing_balance)
                })

                opening_balance = closing_balance

            periodic_repayment = _quantize_money(Decimal(str(schedule[0]["total_due"]))) if schedule else Decimal("0.00")
            total_repayment = P + total_interest + total_fees

        return {
            "principal_amount": float(P),
            "interest_rate_bp": interest_rate_bp,
            "compounding_period": period,
            "term_periods": term_periods,
            "methodology": method,
            "days_per_period": days_per_period,
            "periodic_repayment": float(periodic_repayment),
            "total_interest": float(total_interest),
            "total_fees": float(total_fees),
            "total_repayment": float(total_repayment),
            "start_date": start.isoformat(),
            "due_date": due_date.isoformat(),
            "schedule": schedule
        }

    @staticmethod
    def calculate_early_settlement(
        outstanding_balance: float,
        accrued_interest: float = 0.0,
        settlement_fee: float = 0.0,
        settlement_rebate_pct: float = 0.0,
        original_principal: Optional[float] = None,
        original_total_interest: Optional[float] = None
    ) -> Dict[str, Any]:
        bal = _quantize_money(Decimal(str(outstanding_balance)))
        accrued = _quantize_money(Decimal(str(accrued_interest)))
        fee = _quantize_money(Decimal(str(settlement_fee)))
        rebate_pct = Decimal(str(settlement_rebate_pct)) / Decimal("100")

        gross_settlement = bal + accrued + fee
        rebate = _quantize_money(gross_settlement * rebate_pct)
        net_settlement = max(Decimal("0.00"), gross_settlement - rebate)

        orig_p = Decimal(str(original_principal)) if original_principal is not None else bal
        repaid_p = max(Decimal("0.00"), orig_p - bal)

        orig_i = Decimal(str(original_total_interest)) if original_total_interest is not None else Decimal("0.00")
        interest_saved = max(Decimal("0.00"), orig_i - accrued)

        return {
            "original_principal": float(orig_p),
            "repaid_principal": float(repaid_p),
            "outstanding_principal": float(bal),
            "accrued_interest": float(accrued),
            "settlement_fee": float(fee),
            "rebate_amount": float(rebate),
            "net_settlement_amount": float(net_settlement),
            "interest_saved": float(interest_saved)
        }
