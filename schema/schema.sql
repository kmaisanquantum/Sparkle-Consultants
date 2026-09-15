-- =====================================================================
-- Sparkle Consultants — PostgreSQL Schema
-- Single-business automated online lending platform for Papua New Guinea
-- =====================================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";      -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "citext";        -- case-insensitive text

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- IMMUTABILITY TRIGGERS
CREATE OR REPLACE FUNCTION prevent_modification_or_deletion() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Immutability Violation: Rows in % cannot be updated or deleted.', TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;

-- TENANTS (Single business entity: Sparkle Consultants)
CREATE TABLE IF NOT EXISTS tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name       TEXT NOT NULL,
    registration_number TEXT,
    province            TEXT,
    contact_phone       TEXT,
    contact_email       CITEXT UNIQUE,
    password_hash       TEXT,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    max_interest_rate_bp INTEGER NOT NULL DEFAULT 3000,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- USERS (RBAC roles: owner, admin, underwriter, collections_agent, compliance_officer, customer)
CREATE TABLE IF NOT EXISTS users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
    email               CITEXT UNIQUE NOT NULL,
    password_hash       TEXT NOT NULL,
    role                TEXT NOT NULL DEFAULT 'customer',
    full_name           TEXT NOT NULL,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    mfa_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret          TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- CUSTOMERS (Self-registering borrowers linked to users)
CREATE TABLE IF NOT EXISTS customers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id             UUID UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    phone_hash          CHAR(64) NOT NULL,
    national_id_hash    CHAR(64),
    encrypted_full_name BYTEA NOT NULL,
    encrypted_address   BYTEA,
    encrypted_employer  BYTEA,
    is_public_servant   BOOLEAN NOT NULL DEFAULT FALSE,
    alesco_file_number  TEXT,
    status              TEXT NOT NULL DEFAULT 'active', -- active, suspended, closed
    risk_flag           TEXT NOT NULL DEFAULT 'none',  -- none, watch, high
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, phone_hash)
);

-- CUSTOMER PROFILES
CREATE TABLE IF NOT EXISTS customer_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID UNIQUE NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    date_of_birth       DATE,
    gender              TEXT,
    marital_status      TEXT,
    dependents_count    INTEGER DEFAULT 0,
    residential_status  TEXT,
    province            TEXT,
    district            TEXT,
    ward                TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- KYC RECORDS
CREATE TABLE IF NOT EXISTS kyc_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    id_type             TEXT NOT NULL, -- national_id, passport, drivers_license, work_id
    id_number_hash      CHAR(64),
    status              TEXT NOT NULL DEFAULT 'pending', -- pending, verified, rejected
    document_path       TEXT,
    verified_at         TIMESTAMPTZ,
    verified_by         UUID REFERENCES users(id),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- EMPLOYMENT RECORDS
CREATE TABLE IF NOT EXISTS employment_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    employer_name       TEXT NOT NULL,
    position            TEXT,
    employment_type     TEXT NOT NULL DEFAULT 'full_time', -- full_time, part_time, contract, self_employed
    start_date          DATE,
    pay_frequency       TEXT NOT NULL DEFAULT 'fortnightly', -- weekly, fortnightly, monthly
    alesco_number       TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- INCOME RECORDS
CREATE TABLE IF NOT EXISTS income_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    gross_income_fortnightly NUMERIC(14,2) NOT NULL DEFAULT 0,
    net_income_fortnightly   NUMERIC(14,2) NOT NULL DEFAULT 0,
    secondary_income        NUMERIC(14,2) NOT NULL DEFAULT 0,
    verified                BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- BANK ACCOUNTS
CREATE TABLE IF NOT EXISTS bank_accounts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    bank_name           TEXT NOT NULL, -- BSP, Kina Bank, Westpac, ANZ PNG
    account_number_hash CHAR(64) NOT NULL,
    account_name        TEXT NOT NULL,
    bsb_code            TEXT,
    is_primary          BOOLEAN NOT NULL DEFAULT TRUE,
    verified            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LOAN PRODUCTS
CREATE TABLE IF NOT EXISTS loan_products (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
    code                TEXT UNIQUE NOT NULL,
    name                TEXT NOT NULL,
    description         TEXT,
    min_amount          NUMERIC(14,2) NOT NULL DEFAULT 100,
    max_amount          NUMERIC(14,2) NOT NULL DEFAULT 50000,
    interest_rate_bp    INTEGER NOT NULL DEFAULT 1500, -- BP per compounding period
    min_term            INTEGER NOT NULL DEFAULT 2,
    max_term            INTEGER NOT NULL DEFAULT 52,
    compounding_period  TEXT NOT NULL DEFAULT 'fortnightly',
    admin_fee           NUMERIC(14,2) NOT NULL DEFAULT 50,
    late_fee_bp         INTEGER NOT NULL DEFAULT 500,
    min_income          NUMERIC(14,2) NOT NULL DEFAULT 500,
    max_dti_pct         NUMERIC(5,2) NOT NULL DEFAULT 50.00,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LOAN APPLICATIONS (17-step wizard draft & submitted state)
CREATE TABLE IF NOT EXISTS loan_applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    loan_product_id     UUID REFERENCES loan_products(id) ON DELETE RESTRICT,
    amount_requested    NUMERIC(14,2) NOT NULL,
    term_requested      INTEGER NOT NULL,
    compounding_period  TEXT NOT NULL DEFAULT 'fortnightly',
    purpose             TEXT,
    step_completed      INTEGER NOT NULL DEFAULT 1,
    status              TEXT NOT NULL DEFAULT 'draft', -- draft, submitted, kyc_pending, verification_required, assessment, manual_review, approved, conditionally_approved, declined, offer_issued, offer_accepted, agreement_pending, ready_for_disbursement, disbursing, disbursed, cancelled
    draft_data          JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LOAN OFFERS
CREATE TABLE IF NOT EXISTS loan_offers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id      UUID UNIQUE NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    loan_product_id     UUID REFERENCES loan_products(id) ON DELETE RESTRICT,
    approved_amount     NUMERIC(14,2) NOT NULL,
    interest_rate_bp    INTEGER NOT NULL,
    term_periods        INTEGER NOT NULL,
    compounding_period  TEXT NOT NULL DEFAULT 'fortnightly',
    periodic_repayment  NUMERIC(14,2) NOT NULL,
    total_repayment     NUMERIC(14,2) NOT NULL,
    total_interest      NUMERIC(14,2) NOT NULL,
    fees                NUMERIC(14,2) NOT NULL DEFAULT 0,
    expires_at          TIMESTAMPTZ NOT NULL,
    status              TEXT NOT NULL DEFAULT 'issued', -- issued, accepted, declined, expired
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LOANS
CREATE TABLE IF NOT EXISTS loans (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id           UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    application_id       UUID REFERENCES loan_applications(id) ON DELETE SET NULL,
    offer_id             UUID REFERENCES loan_offers(id) ON DELETE SET NULL,
    loan_product_id       UUID REFERENCES loan_products(id) ON DELETE RESTRICT,

    principal_amount      NUMERIC(14,2) NOT NULL CHECK (principal_amount > 0),
    interest_rate_bp      INTEGER NOT NULL CHECK (interest_rate_bp >= 0),
    compounding_period    TEXT NOT NULL DEFAULT 'fortnightly',
    term_periods          INTEGER NOT NULL CHECK (term_periods > 0),

    periodic_repayment    NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_repayment       NUMERIC(14,2) NOT NULL DEFAULT 0,

    disbursed_at          TIMESTAMPTZ,
    due_at                TIMESTAMPTZ,

    outstanding_balance   NUMERIC(14,2) NOT NULL DEFAULT 0,
    accrued_interest       NUMERIC(14,2) NOT NULL DEFAULT 0,
    status                TEXT NOT NULL DEFAULT 'active', -- draft, submitted, kyc_pending, verification_required, assessment, manual_review, approved, conditionally_approved, declined, offer_issued, offer_accepted, agreement_pending, ready_for_disbursement, disbursing, disbursed, active, completed, defaulted, cancelled

    net_pay_at_disbursement     NUMERIC(14,2),
    total_deduction_pct_at_disbursement NUMERIC(5,2),

    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- LOAN SCHEDULES
CREATE TABLE IF NOT EXISTS loan_schedules (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id             UUID NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    instalment_number   INTEGER NOT NULL,
    due_date            DATE NOT NULL,
    principal_due       NUMERIC(14,2) NOT NULL,
    interest_due        NUMERIC(14,2) NOT NULL,
    fee_due             NUMERIC(14,2) NOT NULL DEFAULT 0,
    total_due           NUMERIC(14,2) NOT NULL,
    paid_amount         NUMERIC(14,2) NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'pending', -- pending, partial, paid, overdue
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(loan_id, instalment_number)
);

-- TRANSACTIONS (Append-only ledger)
CREATE TABLE IF NOT EXISTS transactions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
    loan_id             UUID NOT NULL REFERENCES loans(id) ON DELETE CASCADE,

    type                TEXT NOT NULL, -- disbursement, principal, interest, fee, repayment, reversal, adjustment, waiver, penalty, write_off, refund
    amount              NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    balance_after       NUMERIC(14,2) NOT NULL,

    client_node_id      TEXT,
    client_generated_id UUID NOT NULL,
    client_recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    server_received_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload_signature   TEXT NOT NULL DEFAULT 'SYSTEM_POSTED',
    sync_conflict_state TEXT NOT NULL DEFAULT 'none',
    idempotency_key     TEXT UNIQUE,

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, client_generated_id)
);

-- Attach Immutability Triggers to Transactions
DROP TRIGGER IF EXISTS trg_immutable_transactions ON transactions;
CREATE TRIGGER trg_immutable_transactions
BEFORE UPDATE OR DELETE ON transactions
FOR EACH ROW EXECUTE FUNCTION prevent_modification_or_deletion();

-- PAYMENTS
CREATE TABLE IF NOT EXISTS payments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    loan_id             UUID REFERENCES loans(id) ON DELETE SET NULL,
    amount              NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    currency            TEXT NOT NULL DEFAULT 'PGK',
    payment_method      TEXT NOT NULL DEFAULT 'bsp_online', -- bsp_online, kina_online, bank_transfer, payroll_deduction, cash
    payment_provider    TEXT NOT NULL DEFAULT 'bsp',
    provider_reference  TEXT,
    status              TEXT NOT NULL DEFAULT 'pending', -- pending, successful, failed, reversed
    idempotency_key     TEXT UNIQUE NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- DISBURSEMENTS
CREATE TABLE IF NOT EXISTS disbursements (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
    loan_id             UUID UNIQUE NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    amount              NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    bank_account_id     UUID REFERENCES bank_accounts(id) ON DELETE SET NULL,
    payment_provider    TEXT NOT NULL DEFAULT 'bsp',
    provider_reference  TEXT,
    status              TEXT NOT NULL DEFAULT 'pending', -- pending, processing, disbursed, failed
    disbursed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- PAYMENT RECONCILIATIONS
CREATE TABLE IF NOT EXISTS payment_reconciliations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id          UUID REFERENCES payments(id) ON DELETE SET NULL,
    transaction_id      UUID REFERENCES transactions(id) ON DELETE SET NULL,
    customer_id         UUID REFERENCES customers(id) ON DELETE CASCADE,
    loan_id             UUID REFERENCES loans(id) ON DELETE CASCADE,
    amount              NUMERIC(14,2) NOT NULL,
    currency            TEXT NOT NULL DEFAULT 'PGK',
    reconciliation_date DATE NOT NULL DEFAULT CURRENT_DATE,
    method              TEXT,
    provider            TEXT NOT NULL DEFAULT 'bsp',
    provider_reference  TEXT,
    status              TEXT NOT NULL DEFAULT 'pending',
    reconciliation_status TEXT NOT NULL DEFAULT 'unreconciled', -- pending, successful, failed, reversed, reconciled, unreconciled
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- DOCUMENTS
CREATE TABLE IF NOT EXISTS documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    application_id      UUID REFERENCES loan_applications(id) ON DELETE SET NULL,
    loan_id             UUID REFERENCES loans(id) ON DELETE SET NULL,
    document_type       TEXT NOT NULL, -- payslip, national_id, employment_letter, bank_statement, signed_agreement
    file_path           TEXT NOT NULL,
    file_name           TEXT NOT NULL,
    file_size           INTEGER,
    status              TEXT NOT NULL DEFAULT 'uploaded', -- uploaded, verified, rejected
    uploaded_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- NOTIFICATIONS
CREATE TABLE IF NOT EXISTS notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE,
    customer_id         UUID REFERENCES customers(id) ON DELETE CASCADE,
    title               TEXT NOT NULL,
    message             TEXT NOT NULL,
    channel             TEXT NOT NULL DEFAULT 'in_app', -- in_app, sms, email
    is_read             BOOLEAN NOT NULL DEFAULT FALSE,
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- COLLECTIONS (10 collection stages)
CREATE TABLE IF NOT EXISTS collections (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loan_id             UUID UNIQUE NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    stage               TEXT NOT NULL DEFAULT 'current', -- current, due_soon, due_today, overdue_1_7, overdue_8_30, overdue_31_60, overdue_61_90, serious_arrears, default, recovery
    days_overdue        INTEGER NOT NULL DEFAULT 0,
    amount_overdue      NUMERIC(14,2) NOT NULL DEFAULT 0,
    assigned_agent_id   UUID REFERENCES users(id) ON DELETE SET NULL,
    last_contact_date   DATE,
    next_action_date    DATE,
    notes               TEXT,
    status              TEXT NOT NULL DEFAULT 'open', -- open, closed, escalated
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- COMPLAINTS
CREATE TABLE IF NOT EXISTS complaints (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    category            TEXT NOT NULL, -- fee_dispute, service_delay, collection_conduct, technical_issue, privacy, general
    subject             TEXT NOT NULL,
    description         TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'open', -- open, in_investigation, resolved, closed
    resolution_notes    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at         TIMESTAMPTZ
);

-- DECISION RECORDS
CREATE TABLE IF NOT EXISTS decision_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id      UUID NOT NULL REFERENCES loan_applications(id) ON DELETE CASCADE,
    customer_id         UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    decision            TEXT NOT NULL, -- APPROVE, CONDITIONAL_APPROVAL, MANUAL_REVIEW, DECLINE
    score               INTEGER NOT NULL DEFAULT 700,
    dti_ratio           NUMERIC(5,2),
    reason_codes        JSONB,
    evaluated_rules     JSONB,
    decision_by         TEXT NOT NULL DEFAULT 'AUTOMATED_ENGINE',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RISK PROFILES
CREATE TABLE IF NOT EXISTS risk_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id         UUID UNIQUE NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    risk_tier           TEXT NOT NULL DEFAULT 'low', -- low, medium, high, watch
    risk_score          INTEGER NOT NULL DEFAULT 700,
    max_approved_limit  NUMERIC(14,2) NOT NULL DEFAULT 10000.00,
    watch_reasons       TEXT,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID REFERENCES users(id) ON DELETE SET NULL,
    customer_id         UUID REFERENCES customers(id) ON DELETE SET NULL,
    action              TEXT NOT NULL,
    entity_type         TEXT NOT NULL,
    entity_id           TEXT,
    payload             JSONB,
    ip_address          TEXT,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Attach Immutability Triggers to Audit Logs
DROP TRIGGER IF EXISTS trg_immutable_audit_logs ON audit_logs;
CREATE TRIGGER trg_immutable_audit_logs
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_modification_or_deletion();

-- SYSTEM SETTINGS
CREATE TABLE IF NOT EXISTS system_settings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key                 TEXT UNIQUE NOT NULL,
    value               TEXT NOT NULL,
    description         TEXT,
    category            TEXT NOT NULL DEFAULT 'general',
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- COLLATERAL LOGS (Retained for legacy/optional physical assets)
CREATE TABLE IF NOT EXISTS collateral_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID REFERENCES tenants(id) ON DELETE CASCADE,
    loan_id             UUID NOT NULL REFERENCES loans(id) ON DELETE CASCADE,
    item_description    TEXT NOT NULL,
    item_category       TEXT NOT NULL DEFAULT 'other',
    estimated_value     NUMERIC(12,2),
    storage_location    TEXT NOT NULL,
    custody_status      TEXT NOT NULL DEFAULT 'in_vault',
    received_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    released_at         TIMESTAMPTZ,
    released_to         TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
