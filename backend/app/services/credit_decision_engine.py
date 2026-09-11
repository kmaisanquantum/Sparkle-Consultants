from typing import Dict, List, Any, Optional, Tuple
from app.services.calculation_engine import CalculationEngine
from app.services.payslip_parser import PayslipExtract, check_deduction_ceiling

class CreditDecisionEngine:
    """
    Automated Credit Decision Engine.
    Evaluates loan products, income, debt-to-income (DTI),
    and public service payroll retention limits (Alesco 50% ceiling).
    Outputs: APPROVE, CONDITIONAL_APPROVAL, MANUAL_REVIEW, DECLINE
    """

    @staticmethod
    def evaluate(
        product_code: str,
        requested_amount: float,
        requested_term: int,
        compounding_period: str,
        interest_rate_bp: int,
        admin_fee: float,
        min_amount: float,
        max_amount: float,
        min_income: float,
        max_dti_pct: float,
        fortnightly_net_income: float,
        existing_fortnightly_obligations: float = 0.0,
        is_public_servant: bool = False,
        alesco_file_number: Optional[str] = None,
        gross_pay: Optional[float] = None,
        total_deductions: Optional[float] = None,
        risk_flag: str = "none",
        active_defaults_count: int = 0
    ) -> Dict[str, Any]:
        reason_codes: List[str] = []
        evaluated_rules: Dict[str, Any] = {}
        score = 750

        # Rule 1: Active Defaults
        evaluated_rules["active_defaults_check"] = active_defaults_count
        if active_defaults_count > 0:
            reason_codes.append("DECLINE_ACTIVE_DEFAULT_EXISTS")
            return {
                "decision": "DECLINE",
                "score": 400,
                "dti_ratio": 0.0,
                "reason_codes": reason_codes,
                "evaluated_rules": evaluated_rules,
                "summary": "Application declined due to existing active default on file."
            }

        # Rule 2: Risk Flag
        evaluated_rules["risk_flag"] = risk_flag
        if risk_flag == "high":
            reason_codes.append("DECLINE_HIGH_RISK_FLAG")
            return {
                "decision": "DECLINE",
                "score": 450,
                "dti_ratio": 0.0,
                "reason_codes": reason_codes,
                "evaluated_rules": evaluated_rules,
                "summary": "Application declined due to high risk account profile."
            }

        # Rule 3: Amount Limits
        evaluated_rules["amount_limits"] = {"requested": requested_amount, "min": min_amount, "max": max_amount}
        if requested_amount < min_amount or requested_amount > max_amount:
            reason_codes.append(f"DECLINE_AMOUNT_OUT_OF_BOUNDS_{min_amount}_{max_amount}")
            return {
                "decision": "DECLINE",
                "score": 500,
                "dti_ratio": 0.0,
                "reason_codes": reason_codes,
                "evaluated_rules": evaluated_rules,
                "summary": f"Requested amount K{requested_amount} outside product bounds (K{min_amount} - K{max_amount})."
            }

        # Rule 4: Minimum Income Check
        evaluated_rules["income_check"] = {"net_income": fortnightly_net_income, "min_required": min_income}
        if fortnightly_net_income < min_income:
            reason_codes.append("DECLINE_INSUFFICIENT_MIN_INCOME")
            return {
                "decision": "DECLINE",
                "score": 520,
                "dti_ratio": 0.0,
                "reason_codes": reason_codes,
                "evaluated_rules": evaluated_rules,
                "summary": f"Fortnightly income K{fortnightly_net_income} is below product threshold K{min_income}."
            }

        # Calculation Engine call
        calc = CalculationEngine.calculate_loan_summary(
            principal_amount=requested_amount,
            interest_rate_bp=interest_rate_bp,
            compounding_period=compounding_period,
            term_periods=requested_term,
            admin_fee=admin_fee
        )
        periodic_repayment = calc["periodic_repayment"]

        # Convert repayment to fortnightly equivalent for standard DTI comparison
        period = compounding_period.lower()
        if period == "weekly":
            fn_repayment = periodic_repayment * 2.0
        elif period == "monthly":
            fn_repayment = periodic_repayment / 2.166
        else:
            fn_repayment = periodic_repayment

        total_fortnightly_debt = existing_fortnightly_obligations + fn_repayment
        dti_ratio = round((total_fortnightly_debt / fortnightly_net_income) * 100.0, 2) if fortnightly_net_income > 0 else 100.0
        evaluated_rules["dti"] = {"dti_ratio_pct": dti_ratio, "max_allowed_pct": max_dti_pct}

        if dti_ratio > max_dti_pct:
            reason_codes.append(f"DECLINE_DTI_EXCEEDED_{dti_ratio}_VS_{max_dti_pct}")
            return {
                "decision": "DECLINE",
                "score": 550,
                "dti_ratio": dti_ratio,
                "reason_codes": reason_codes,
                "evaluated_rules": evaluated_rules,
                "summary": f"Proposed Debt-To-Income ratio ({dti_ratio}%) exceeds maximum limit ({max_dti_pct}%)."
            }

        # Rule 5: Alesco 50% net pay retention ceiling check for Public Servants
        if is_public_servant:
            if gross_pay is None or total_deductions is None:
                reason_codes.append("MANUAL_REVIEW_PUBLIC_SERVANT_PAYSLIP_REQUIRED")
                return {
                    "decision": "MANUAL_REVIEW",
                    "score": 650,
                    "dti_ratio": dti_ratio,
                    "reason_codes": reason_codes,
                    "evaluated_rules": evaluated_rules,
                    "summary": "Public servant application requires payslip upload for Alesco ceiling verification."
                }

            extract = PayslipExtract(
                employee_name=None,
                alesco_file_number=alesco_file_number,
                gross_pay=gross_pay,
                net_pay=gross_pay - total_deductions,
                total_deductions=total_deductions,
                reconciliation_ok=True,
                needs_manual_review=False
            )
            within_ceiling, resulting_pct = check_deduction_ceiling(extract, fn_repayment)
            evaluated_rules["alesco_ceiling"] = {"within_ceiling": within_ceiling, "resulting_pct": resulting_pct}

            if not within_ceiling:
                reason_codes.append(f"DECLINE_ALESCO_CEILING_EXCEEDED_{resulting_pct}_PCT")
                return {
                    "decision": "DECLINE",
                    "score": 580,
                    "dti_ratio": dti_ratio,
                    "reason_codes": reason_codes,
                    "evaluated_rules": evaluated_rules,
                    "summary": f"Alesco 50% net pay retention check failed: total deductions would reach {resulting_pct}%."
                }

        # Score Adjustments
        if risk_flag == "watch":
            score -= 50
            reason_codes.append("CONDITIONAL_APPROVAL_WATCH_ACCOUNT")
            return {
                "decision": "CONDITIONAL_APPROVAL",
                "score": score,
                "dti_ratio": dti_ratio,
                "reason_codes": reason_codes,
                "evaluated_rules": evaluated_rules,
                "summary": "Approved conditionally due to watch status on account history."
            }

        if dti_ratio > 40.0:
            score -= 30
            reason_codes.append("APPROVE_HIGH_DTI_MARGIN")

        reason_codes.append("APPROVE_CREDIT_METRICS_PASSED")
        return {
            "decision": "APPROVE",
            "score": score,
            "dti_ratio": dti_ratio,
            "reason_codes": reason_codes,
            "evaluated_rules": evaluated_rules,
            "summary": "Application automatically approved based on credit score, DTI, and income checks."
        }
