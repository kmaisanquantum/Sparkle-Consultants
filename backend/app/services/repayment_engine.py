from datetime import datetime, timezone
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.orm import Loan, Transaction, LoanSchedule

class RepaymentEngine:
    @staticmethod
    async def process_repayment(
        db: AsyncSession,
        loan: Loan,
        amount: float,
        payment_method: str = "bsp_online",
        idempotency_key: str = None,
        notes: str = None
    ) -> Dict[str, Any]:
        if amount <= 0:
            raise ValueError("Repayment amount must be positive")

        current_balance = float(loan.outstanding_balance)
        new_balance = max(0.0, round(current_balance - amount, 2))

        # Check for existing transaction idempotency
        if idempotency_key:
            stmt = select(Transaction).where(Transaction.idempotency_key == idempotency_key)
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                return {
                    "transaction_id": str(existing.id),
                    "amount": float(existing.amount),
                    "balance_after": float(existing.balance_after),
                    "loan_status": loan.status,
                    "duplicate": True
                }

        loan.outstanding_balance = new_balance
        if new_balance == 0.0 and loan.status in ("active", "overdue", "defaulted"):
            loan.status = "completed"

        txn = Transaction(
            tenant_id=loan.tenant_id,
            loan_id=loan.id,
            type="repayment",
            amount=amount,
            balance_after=new_balance,
            client_node_id="SYSTEM",
            client_recorded_at=datetime.now(timezone.utc),
            payload_signature="SYSTEM_POSTED",
            idempotency_key=idempotency_key,
            notes=notes or f"Repayment recorded via {payment_method}"
        )
        db.add(txn)

        # Update schedules in order
        remaining_repayment = amount
        schedules_stmt = (
            select(LoanSchedule)
            .where(LoanSchedule.loan_id == loan.id)
            .order_by(LoanSchedule.instalment_number)
        )
        schedules = (await db.execute(schedules_stmt)).scalars().all()

        for sched in schedules:
            if remaining_repayment <= 0:
                break
            due = float(sched.total_due) - float(sched.paid_amount)
            if due > 0:
                applied = min(remaining_repayment, due)
                sched.paid_amount = float(sched.paid_amount) + applied
                remaining_repayment -= applied
                if float(sched.paid_amount) >= float(sched.total_due):
                    sched.status = "paid"
                else:
                    sched.status = "partial"

        await db.commit()
        await db.refresh(txn)

        return {
            "transaction_id": str(txn.id),
            "loan_id": str(loan.id),
            "amount": amount,
            "balance_after": new_balance,
            "loan_status": loan.status,
            "duplicate": False
        }
