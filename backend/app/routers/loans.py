import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.crypto import decrypt_field
from app.models.orm import Loan, Customer, Transaction, User
from app.routers.auth import get_current_user, require_roles
from app.services.payslip_parser import PayslipExtract, check_deduction_ceiling

router = APIRouter(prefix="/api/v1/loans", tags=["loans"])


class LoanCreate(BaseModel):
    customer_id: str
    principal_amount: float
    interest_rate_bp: int
    compounding_period: str = "fortnightly"
    term_periods: int
    gross_pay: Optional[float] = None
    total_deductions: Optional[float] = None


class LoanOut(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    principal_amount: float
    interest_rate_bp: int
    compounding_period: str
    term_periods: int
    outstanding_balance: float
    status: str
    disbursed_at: Optional[datetime]
    due_at: Optional[datetime]
    net_pay_at_disbursement: Optional[float]
    total_deduction_pct_at_disbursement: Optional[float]


class RepaymentCreate(BaseModel):
    amount: float
    notes: Optional[str] = None


class RepaymentOut(BaseModel):
    id: str
    loan_id: str
    amount: float
    balance_after: float
    notes: Optional[str]
    created_at: datetime


@router.get("", response_model=List[LoanOut])
async def list_loans(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Loan).options(joinedload(Loan.customer))

    if current_user.role == "customer":
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if not cust_id:
            return []
        stmt = stmt.where(Loan.customer_id == cust_id)

    res = await db.execute(stmt)
    loans = res.scalars().all()

    output = []
    for l in loans:
        c = l.customer
        customer_name = decrypt_field(c.encrypted_full_name) if c and c.encrypted_full_name else "Customer"

        output.append(
            LoanOut(
                id=str(l.id),
                customer_id=str(l.customer_id),
                customer_name=customer_name,
                principal_amount=float(l.principal_amount),
                interest_rate_bp=l.interest_rate_bp,
                compounding_period=l.compounding_period,
                term_periods=l.term_periods,
                outstanding_balance=float(l.outstanding_balance),
                status=l.status,
                disbursed_at=l.disbursed_at,
                due_at=l.due_at,
                net_pay_at_disbursement=float(l.net_pay_at_disbursement) if l.net_pay_at_disbursement else None,
                total_deduction_pct_at_disbursement=float(l.total_deduction_pct_at_disbursement) if l.total_deduction_pct_at_disbursement else None,
            )
        )

    return output


@router.get("/{id}", response_model=LoanOut)
async def get_loan(
    id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Loan).options(joinedload(Loan.customer)).where(Loan.id == uuid.UUID(id))
    loan = (await db.execute(stmt)).scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if current_user.role == "customer":
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if loan.customer_id != cust_id:
            raise HTTPException(status_code=403, detail="Access denied to this loan record")

    c = loan.customer
    customer_name = decrypt_field(c.encrypted_full_name) if c and c.encrypted_full_name else "Customer"

    return LoanOut(
        id=str(loan.id),
        customer_id=str(loan.customer_id),
        customer_name=customer_name,
        principal_amount=float(loan.principal_amount),
        interest_rate_bp=loan.interest_rate_bp,
        compounding_period=loan.compounding_period,
        term_periods=loan.term_periods,
        outstanding_balance=float(loan.outstanding_balance),
        status=loan.status,
        disbursed_at=loan.disbursed_at,
        due_at=loan.due_at,
        net_pay_at_disbursement=float(loan.net_pay_at_disbursement) if loan.net_pay_at_disbursement else None,
        total_deduction_pct_at_disbursement=float(loan.total_deduction_pct_at_disbursement) if loan.total_deduction_pct_at_disbursement else None,
    )


@router.post("/{id}/repayments", response_model=RepaymentOut)
async def record_repayment(
    id: str,
    body: RepaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    loan_stmt = select(Loan).where(Loan.id == uuid.UUID(id))
    loan = (await db.execute(loan_stmt)).scalar_one_or_none()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if current_user.role == "customer":
        cust_stmt = select(Customer.id).where(Customer.user_id == current_user.id)
        cust_id = (await db.execute(cust_stmt)).scalar_one_or_none()
        if loan.customer_id != cust_id:
            raise HTTPException(status_code=403, detail="Access denied")

    new_balance = float(loan.outstanding_balance) - body.amount
    if new_balance < 0:
        new_balance = 0.0

    loan.outstanding_balance = new_balance
    if new_balance <= 0 and loan.status in ("active", "overdue"):
        loan.status = "closed"

    txn = Transaction(
        tenant_id=loan.tenant_id,
        loan_id=loan.id,
        type="repayment",
        amount=body.amount,
        balance_after=new_balance,
        client_node_id="SYSTEM",
        client_generated_id=uuid.uuid4(),
        client_recorded_at=datetime.utcnow(),
        payload_signature="SYSTEM_POSTED",
        notes=body.notes,
    )

    db.add(txn)
    await db.commit()
    await db.refresh(txn)

    return RepaymentOut(
        id=str(txn.id),
        loan_id=str(txn.loan_id),
        amount=float(txn.amount),
        balance_after=float(txn.balance_after),
        notes=txn.notes,
        created_at=txn.created_at,
    )
