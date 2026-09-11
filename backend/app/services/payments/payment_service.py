import uuid
from datetime import datetime, timezone, date
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.orm import Payment, PaymentReconciliation, Loan
from app.services.payments.bsp_provider import BSPPaymentProvider
from app.services.repayment_engine import RepaymentEngine

class PaymentService:
    def __init__(self, provider: Optional[Any] = None):
        self.provider = provider or BSPPaymentProvider()

    async def process_repayment_payment(
        self,
        db: AsyncSession,
        customer_id: str,
        loan_id: str,
        amount: float,
        payment_method: str = "bsp_online",
        idempotency_key: str = None
    ) -> Dict[str, Any]:
        idem_key = idempotency_key or f"PAY-{uuid.uuid4()}"

        # 1. Idempotency check on payments table
        stmt = select(Payment).where(Payment.idempotency_key == idem_key)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            return {
                "payment_id": str(existing.id),
                "status": existing.status,
                "amount": float(existing.amount),
                "duplicate": True
            }

        # 2. Initiate via provider adapter
        result = await self.provider.initiate_collection(
            amount=amount,
            currency="PGK",
            customer_reference=customer_id,
            idempotency_key=idem_key
        )

        # 3. Save Payment record
        payment = Payment(
            customer_id=uuid.UUID(customer_id),
            loan_id=uuid.UUID(loan_id) if loan_id else None,
            amount=amount,
            currency="PGK",
            payment_method=payment_method,
            payment_provider="bsp",
            provider_reference=result.get("provider_reference"),
            status="successful",
            idempotency_key=idem_key
        )
        db.add(payment)
        await db.flush()

        # 4. Post to Loan Repayment Ledger if loan specified
        txn_id = None
        if loan_id:
            loan_stmt = select(Loan).where(Loan.id == uuid.UUID(loan_id))
            loan = (await db.execute(loan_stmt)).scalar_one_or_none()
            if loan:
                repayment_res = await RepaymentEngine.process_repayment(
                    db=db,
                    loan=loan,
                    amount=amount,
                    payment_method=payment_method,
                    idempotency_key=f"TXN-{idem_key}",
                    notes=f"Repayment via {payment_method} Ref: {result.get('provider_reference')}"
                )
                txn_id = repayment_res.get("transaction_id")

        # 5. Record Payment Reconciliation
        reconcile = PaymentReconciliation(
            payment_id=payment.id,
            transaction_id=uuid.UUID(txn_id) if txn_id else None,
            customer_id=payment.customer_id,
            loan_id=payment.loan_id,
            amount=amount,
            currency="PGK",
            reconciliation_date=date.today(),
            method=payment_method,
            provider="bsp",
            provider_reference=result.get("provider_reference"),
            status="successful",
            reconciliation_status="reconciled",
            notes="Automated BSP reconciliation matched against active loan ledger."
        )
        db.add(reconcile)

        await db.commit()
        await db.refresh(payment)

        return {
            "payment_id": str(payment.id),
            "status": payment.status,
            "provider_reference": payment.provider_reference,
            "reconciliation_status": "reconciled",
            "duplicate": False
        }
