from datetime import datetime, timezone
from typing import Dict, Any

class AgreementService:
    @staticmethod
    def generate_agreement_document(
        customer_name: str,
        national_id_or_phone: str,
        principal_amount: float,
        periodic_repayment: float,
        term_periods: int,
        compounding_period: str,
        total_repayment: float
    ) -> Dict[str, Any]:
        contract_text = (
            f"SPARKLE CONSULTANTS ONLINE LENDING AGREEMENT\n\n"
            f"Borrower Name: {customer_name}\n"
            f"Borrower Identity Ref: {national_id_or_phone}\n\n"
            f"Loan Principal: PGK {principal_amount:,.2f}\n"
            f"Compounding Period: {compounding_period.title()}\n"
            f"Number of Instalments: {term_periods}\n"
            f"Periodic Instalment Amount: PGK {periodic_repayment:,.2f}\n"
            f"Total Repayment Amount: PGK {total_repayment:,.2f}\n\n"
            f"TERMS & CONDITIONS:\n"
            f"1. The Borrower agrees to repay the Total Repayment Amount in accordance with the specified schedule.\n"
            f"2. Payments will be processed online or via direct salary/bank deduction.\n"
            f"3. Late payments will incur standard late fees as prescribed under Sparkle Consultants system rules.\n"
            f"4. This digital agreement is legally binding upon electronic signature.\n"
        )

        return {
            "document_title": "Sparkle Consultants Digital Loan Agreement",
            "content": contract_text,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def record_electronic_signature(
        agreement_id: str,
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        signed_at = datetime.now(timezone.utc)
        return {
            "agreement_id": agreement_id,
            "signed_at": signed_at.isoformat(),
            "ip_address": ip_address,
            "user_agent": user_agent,
            "signature_hash": f"SIG-{hash(agreement_id + signed_at.isoformat())}"
        }
