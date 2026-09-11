from datetime import datetime, timedelta, date, timezone
from typing import Dict, List, Any, Optional
from math import ceil

class CalculationEngine:
    """
    Authoritative server-side financial calculation engine.
    No financial math is allowed on the frontend.
    """

    @staticmethod
    def calculate_loan_summary(
        principal_amount: float,
        interest_rate_bp: int,
        compounding_period: str,
        term_periods: int,
        admin_fee: float = 0.0,
        start_date: Optional[date] = None
    ) -> Dict[str, Any]:
        if principal_amount <= 0:
            raise ValueError("Principal amount must be greater than zero")
        if term_periods <= 0:
            raise ValueError("Term periods must be greater than zero")

        period = compounding_period.lower()
        if period == "weekly":
            days_per_period = 7
        elif period == "monthly":
            days_per_period = 30
        else: # fortnightly default
            days_per_period = 14

        # Total interest = Principal * (Interest BP / 10000)
        total_interest = round(principal_amount * (interest_rate_bp / 10000.0), 2)
        total_fees = round(float(admin_fee), 2)
        total_repayment = round(principal_amount + total_interest + total_fees, 2)

        # Periodic repayment
        periodic_repayment = round(total_repayment / term_periods, 2)

        start = start_date or date.today()
        due_date = start + timedelta(days=days_per_period * term_periods)

        # Generate schedule
        schedule: List[Dict[str, Any]] = []
        principal_per_period = round(principal_amount / term_periods, 2)
        interest_per_period = round(total_interest / term_periods, 2)
        fee_per_period = round(total_fees / term_periods, 2)

        accumulated_principal = 0.0
        accumulated_interest = 0.0
        accumulated_fee = 0.0

        for i in range(1, term_periods + 1):
            inst_due_date = start + timedelta(days=days_per_period * i)

            if i == term_periods:
                # Adjust last instalment for rounding precision
                p_due = round(principal_amount - accumulated_principal, 2)
                i_due = round(total_interest - accumulated_interest, 2)
                f_due = round(total_fees - accumulated_fee, 2)
            else:
                p_due = principal_per_period
                i_due = interest_per_period
                f_due = fee_per_period
                accumulated_principal += p_due
                accumulated_interest += i_due
                accumulated_fee += f_due

            t_due = round(p_due + i_due + f_due, 2)
            schedule.append({
                "instalment_number": i,
                "due_date": inst_due_date.isoformat(),
                "principal_due": p_due,
                "interest_due": i_due,
                "fee_due": f_due,
                "total_due": t_due
            })

        return {
            "principal_amount": round(principal_amount, 2),
            "interest_rate_bp": interest_rate_bp,
            "compounding_period": period,
            "term_periods": term_periods,
            "days_per_period": days_per_period,
            "periodic_repayment": periodic_repayment,
            "total_interest": total_interest,
            "total_fees": total_fees,
            "total_repayment": total_repayment,
            "start_date": start.isoformat(),
            "due_date": due_date.isoformat(),
            "schedule": schedule
        }

    @staticmethod
    def calculate_early_settlement(
        outstanding_balance: float,
        accrued_interest: float = 0.0,
        settlement_rebate_pct: float = 0.0
    ) -> Dict[str, Any]:
        gross_settlement = outstanding_balance + accrued_interest
        rebate = round(gross_settlement * (settlement_rebate_pct / 100.0), 2)
        net_settlement = round(gross_settlement - rebate, 2)

        return {
            "outstanding_principal": round(outstanding_balance, 2),
            "accrued_interest": round(accrued_interest, 2),
            "rebate_amount": rebate,
            "net_settlement_amount": max(0.0, net_settlement)
        }
