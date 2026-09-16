import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer,
    LargeBinary, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


def uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Tenant(Base):
    __tablename__ = "tenants"

    id = uuid_pk()
    business_name = Column(Text, nullable=False)
    registration_number = Column(Text)
    province = Column(Text)
    contact_phone = Column(Text)
    contact_email = Column(Text, unique=True)
    password_hash = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True)
    max_interest_rate_bp = Column(Integer, nullable=False, default=3000)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    users = relationship("User", back_populates="tenant")
    customers = relationship("Customer", back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    email = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    role = Column(String, nullable=False, default="customer") # owner, admin, underwriter, collections_agent, compliance_officer, customer
    full_name = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    mfa_enabled = Column(Boolean, nullable=False, default=False)
    mfa_secret = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="users")
    customer = relationship("Customer", back_populates="user", uselist=False)


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("tenant_id", "phone_hash", name="uq_customer_tenant_phone"),)

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), unique=True, nullable=True)

    phone_hash = Column(String(64), nullable=False)
    national_id_hash = Column(String(64), nullable=True)

    encrypted_full_name = Column(LargeBinary, nullable=False)
    encrypted_address = Column(LargeBinary, nullable=True)
    encrypted_employer = Column(LargeBinary, nullable=True)

    is_public_servant = Column(Boolean, nullable=False, default=False)
    alesco_file_number = Column(Text, nullable=True)

    status = Column(Text, nullable=False, default="active")
    risk_flag = Column(Text, nullable=False, default="none")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="customers")
    user = relationship("User", back_populates="customer")
    profile = relationship("CustomerProfile", back_populates="customer", uselist=False)
    kyc_records = relationship("KYCRecord", back_populates="customer")
    employment_records = relationship("EmploymentRecord", back_populates="customer")
    income_records = relationship("IncomeRecord", back_populates="customer")
    bank_accounts = relationship("BankAccount", back_populates="customer")
    applications = relationship("LoanApplication", back_populates="customer")
    loans = relationship("Loan", back_populates="customer")
    payments = relationship("Payment", back_populates="customer")
    risk_profile = relationship("RiskProfile", back_populates="customer", uselist=False)


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(Text, nullable=True)
    marital_status = Column(Text, nullable=True)
    dependents_count = Column(Integer, default=0)
    residential_status = Column(Text, nullable=True)
    province = Column(Text, nullable=True)
    district = Column(Text, nullable=True)
    ward = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="profile")


class KYCRecord(Base):
    __tablename__ = "kyc_records"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    id_type = Column(Text, nullable=False)
    id_number_hash = Column(String(64), nullable=True)
    status = Column(Text, nullable=False, default="pending")
    document_path = Column(Text, nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="kyc_records")


class EmploymentRecord(Base):
    __tablename__ = "employment_records"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    employer_name = Column(Text, nullable=False)
    position = Column(Text, nullable=True)
    employment_type = Column(Text, nullable=False, default="full_time")
    start_date = Column(Date, nullable=True)
    pay_frequency = Column(Text, nullable=False, default="fortnightly")
    alesco_number = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="employment_records")


class IncomeRecord(Base):
    __tablename__ = "income_records"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    gross_income_fortnightly = Column(Numeric(14, 2), nullable=False, default=0)
    net_income_fortnightly = Column(Numeric(14, 2), nullable=False, default=0)
    secondary_income = Column(Numeric(14, 2), nullable=False, default=0)
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="income_records")


class BankAccount(Base):
    __tablename__ = "bank_accounts"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    bank_name = Column(Text, nullable=False)
    account_number_hash = Column(String(64), nullable=False)
    account_name = Column(Text, nullable=False)
    bsb_code = Column(Text, nullable=True)
    is_primary = Column(Boolean, nullable=False, default=True)
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="bank_accounts")


class LoanProduct(Base):
    __tablename__ = "loan_products"

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    code = Column(Text, unique=True, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    min_amount = Column(Numeric(14, 2), nullable=False, default=100)
    max_amount = Column(Numeric(14, 2), nullable=False, default=50000)
    interest_rate_bp = Column(Integer, nullable=False, default=1500)
    min_term = Column(Integer, nullable=False, default=2)
    max_term = Column(Integer, nullable=False, default=52)
    compounding_period = Column(Text, nullable=False, default="fortnightly")
    admin_fee = Column(Numeric(14, 2), nullable=False, default=50)
    late_fee_bp = Column(Integer, nullable=False, default=500)
    min_income = Column(Numeric(14, 2), nullable=False, default=500)
    max_dti_pct = Column(Numeric(5, 2), nullable=False, default=50.00)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    loan_product_id = Column(UUID(as_uuid=True), ForeignKey("loan_products.id", ondelete="RESTRICT"), nullable=True)
    amount_requested = Column(Numeric(14, 2), nullable=False)
    term_requested = Column(Integer, nullable=False)
    compounding_period = Column(Text, nullable=False, default="fortnightly")
    purpose = Column(Text, nullable=True)
    step_completed = Column(Integer, nullable=False, default=1)
    status = Column(Text, nullable=False, default="draft")
    draft_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="applications")
    offer = relationship("LoanOffer", back_populates="application", uselist=False)
    loan = relationship("Loan", back_populates="application", uselist=False)


class LoanOffer(Base):
    __tablename__ = "loan_offers"

    id = uuid_pk()
    application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    loan_product_id = Column(UUID(as_uuid=True), ForeignKey("loan_products.id", ondelete="RESTRICT"), nullable=True)
    approved_amount = Column(Numeric(14, 2), nullable=False)
    interest_rate_bp = Column(Integer, nullable=False)
    term_periods = Column(Integer, nullable=False)
    compounding_period = Column(Text, nullable=False, default="fortnightly")
    periodic_repayment = Column(Numeric(14, 2), nullable=False)
    total_repayment = Column(Numeric(14, 2), nullable=False)
    total_interest = Column(Numeric(14, 2), nullable=False)
    fees = Column(Numeric(14, 2), nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    status = Column(Text, nullable=False, default="issued")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    calculation_methodology = Column(Text, nullable=False, default="reducing_balance")
    calculation_snapshot = Column(JSONB, nullable=True)

    application = relationship("LoanApplication", back_populates="offer")


class Loan(Base):
    __tablename__ = "loans"

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="SET NULL"), nullable=True)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("loan_offers.id", ondelete="SET NULL"), nullable=True)
    loan_product_id = Column(UUID(as_uuid=True), ForeignKey("loan_products.id", ondelete="RESTRICT"), nullable=True)

    principal_amount = Column(Numeric(14, 2), nullable=False)
    interest_rate_bp = Column(Integer, nullable=False)
    compounding_period = Column(String, nullable=False, default="fortnightly")
    term_periods = Column(Integer, nullable=False)

    periodic_repayment = Column(Numeric(14, 2), nullable=False, default=0)
    total_repayment = Column(Numeric(14, 2), nullable=False, default=0)

    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    due_at = Column(DateTime(timezone=True), nullable=True)

    outstanding_balance = Column(Numeric(14, 2), nullable=False, default=0)
    accrued_interest = Column(Numeric(14, 2), nullable=False, default=0)
    status = Column(String, nullable=False, default="active")

    net_pay_at_disbursement = Column(Numeric(14, 2), nullable=True)
    total_deduction_pct_at_disbursement = Column(Numeric(5, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    calculation_methodology = Column(Text, nullable=False, default="reducing_balance")
    calculation_snapshot = Column(JSONB, nullable=True)

    customer = relationship("Customer", back_populates="loans")
    application = relationship("LoanApplication", back_populates="loan")
    schedules = relationship("LoanSchedule", back_populates="loan", order_by="LoanSchedule.instalment_number")
    collateral = relationship("CollateralLog", back_populates="loan")
    transactions = relationship("Transaction", back_populates="loan")


class LoanSchedule(Base):
    __tablename__ = "loan_schedules"
    __table_args__ = (UniqueConstraint("loan_id", "instalment_number", name="uq_loan_instalment"),)

    id = uuid_pk()
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)
    instalment_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    principal_due = Column(Numeric(14, 2), nullable=False)
    interest_due = Column(Numeric(14, 2), nullable=False)
    fee_due = Column(Numeric(14, 2), nullable=False, default=0)
    total_due = Column(Numeric(14, 2), nullable=False)
    paid_amount = Column(Numeric(14, 2), nullable=False, default=0)
    status = Column(Text, nullable=False, default="pending")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    loan = relationship("Loan", back_populates="schedules")


class CollateralLog(Base):
    __tablename__ = "collateral_logs"

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)

    item_description = Column(Text, nullable=False)
    item_category = Column(String, nullable=False, default="other")
    estimated_value = Column(Numeric(12, 2))
    storage_location = Column(Text, nullable=False)
    custody_status = Column(String, nullable=False, default="in_vault")

    received_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    released_at = Column(DateTime(timezone=True))
    released_to = Column(Text)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    loan = relationship("Loan", back_populates="collateral")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_txn_amount_positive"),
    )

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=False)

    type = Column(String, nullable=False) # disbursement, principal, interest, fee, repayment, reversal, adjustment, waiver, penalty, write_off, refund
    amount = Column(Numeric(14, 2), nullable=False)
    balance_after = Column(Numeric(14, 2), nullable=False)

    client_node_id = Column(Text, nullable=True)
    client_generated_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    client_recorded_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    server_received_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    payload_signature = Column(Text, nullable=False, default="SYSTEM_POSTED")
    sync_conflict_state = Column(String, nullable=False, default="none")
    idempotency_key = Column(Text, unique=True, nullable=True)

    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    loan = relationship("Loan", back_populates="transactions")


class Payment(Base):
    __tablename__ = "payments"

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="SET NULL"), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(Text, nullable=False, default="PGK")
    payment_method = Column(Text, nullable=False, default="bsp_online")
    payment_provider = Column(Text, nullable=False, default="bsp")
    provider_reference = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    idempotency_key = Column(Text, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="payments")


class Disbursement(Base):
    __tablename__ = "disbursements"

    id = uuid_pk()
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Numeric(14, 2), nullable=False)
    bank_account_id = Column(UUID(as_uuid=True), ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True)
    payment_provider = Column(Text, nullable=False, default="bsp")
    provider_reference = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    disbursed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentReconciliation(Base):
    __tablename__ = "payment_reconciliations"

    id = uuid_pk()
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL"), nullable=True)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), nullable=True)
    amount = Column(Numeric(14, 2), nullable=False)
    currency = Column(Text, nullable=False, default="PGK")
    reconciliation_date = Column(Date, nullable=False, default=datetime.utcnow)
    method = Column(Text, nullable=True)
    provider = Column(Text, nullable=False, default="bsp")
    provider_reference = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="pending")
    reconciliation_status = Column(Text, nullable=False, default="unreconciled") # pending, successful, failed, reversed, reconciled, unreconciled
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Document(Base):
    __tablename__ = "documents"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="SET NULL"), nullable=True)
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="SET NULL"), nullable=True)
    document_type = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    file_name = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    status = Column(Text, nullable=False, default="uploaded")
    uploaded_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True)
    title = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(Text, nullable=False, default="in_app")
    is_read = Column(Boolean, nullable=False, default=False)
    sent_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Collection(Base):
    __tablename__ = "collections"

    id = uuid_pk()
    loan_id = Column(UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), unique=True, nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    stage = Column(Text, nullable=False, default="current") # current, due_soon, due_today, overdue_1_7, overdue_8_30, overdue_31_60, overdue_61_90, serious_arrears, default, recovery
    days_overdue = Column(Integer, nullable=False, default=0)
    amount_overdue = Column(Numeric(14, 2), nullable=False, default=0)
    assigned_agent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_contact_date = Column(Date, nullable=True)
    next_action_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Text, nullable=False, default="open")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class Complaint(Base):
    __tablename__ = "complaints"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    category = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="open")
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at = Column(DateTime(timezone=True), nullable=True)


class DecisionRecord(Base):
    __tablename__ = "decision_records"

    id = uuid_pk()
    application_id = Column(UUID(as_uuid=True), ForeignKey("loan_applications.id", ondelete="CASCADE"), nullable=False)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    decision = Column(Text, nullable=False) # APPROVE, CONDITIONAL_APPROVAL, MANUAL_REVIEW, DECLINE
    score = Column(Integer, nullable=False, default=700)
    dti_ratio = Column(Numeric(5, 2), nullable=True)
    reason_codes = Column(JSONB, nullable=True)
    evaluated_rules = Column(JSONB, nullable=True)
    decision_by = Column(Text, nullable=False, default="AUTOMATED_ENGINE")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class RiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = uuid_pk()
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False)
    risk_tier = Column(Text, nullable=False, default="low")
    risk_score = Column(Integer, nullable=False, default=700)
    max_approved_limit = Column(Numeric(14, 2), nullable=False, default=10000.00)
    watch_reasons = Column(Text, nullable=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="risk_profile")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    action = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Text, nullable=True)
    payload = Column(JSONB, nullable=True)
    ip_address = Column(Text, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=datetime.utcnow)


# Alias Borrower to Customer for backward compatibility with existing credit check pipeline
Borrower = Customer

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = uuid_pk()
    key = Column(Text, unique=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Text, nullable=False, default="general")
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
