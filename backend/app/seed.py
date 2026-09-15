import uuid
import secrets
import string
from datetime import datetime, timedelta, timezone, date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.crypto import hash_password, encrypt_field, hash_phone
from app.models.orm import (
    Tenant, User, Customer, CustomerProfile, KYCRecord, EmploymentRecord,
    IncomeRecord, BankAccount, LoanProduct, LoanApplication, LoanOffer,
    Loan, LoanSchedule, Transaction, SystemSetting, RiskProfile, AuditLog, Collection
)


async def seed_data():
    async with AsyncSessionLocal() as db:
        admin_email = "admin@dspng.tech"
        stmt = select(User).where(User.email == admin_email)
        result = await db.execute(stmt)
        existing_admin = result.scalar_one_or_none()

        # Determine admin password from config/env
        admin_password = settings.seed_admin_password or "kilomike@2024"

        if existing_admin:
            print(f"Seed administrator user '{admin_email}' already exists. Updating password hash...")
            existing_admin.password_hash = hash_password(admin_password)
            existing_admin.role = "administrator"
            await db.commit()
            return

        print("Seeding Sparkle Consultants online lending platform database...")

        # 1. Create Tenant / Business
        tenant_id = uuid.uuid4()
        tenant = Tenant(
            id=tenant_id,
            business_name="Sparkle Consultants",
            registration_number="REG-PNG-2024-SPARKLE",
            province="National Capital District",
            contact_phone="+675 321 0000",
            contact_email="info@sparkleconsultants.com",
            is_active=True,
            max_interest_rate_bp=3000,
        )
        db.add(tenant)

        # 2. Create Platform Administrator
        admin_user_id = uuid.uuid4()
        admin_user = User(
            id=admin_user_id,
            tenant_id=tenant_id,
            email=admin_email,
            password_hash=hash_password(admin_password),
            role="administrator",
            full_name="Platform Administrator",
            is_active=True,
        )
        db.add(admin_user)

        # 3. Create System Settings
        settings_seed = [
            SystemSetting(key="business_name", value="Sparkle Consultants", category="general", description="Trading business name"),
            SystemSetting(key="tagline", value="A fully online lending service for Papua New Guinea.", category="general", description="Customer tagline"),
            SystemSetting(key="alesco_max_total_deduction_pct", value="50.00", category="compliance", description="Alesco public servant net pay retention ceiling percentage"),
            SystemSetting(key="bsp_merchant_id", value="SPARKLE_PNG_01", category="payments", description="BSP online payment merchant identifier"),
            SystemSetting(key="bsp_environment", value="sandbox", category="payments", description="BSP gateway environment mode"),
            SystemSetting(key="auto_decision_enabled", value="true", category="decision_engine", description="Enable automated credit scoring and instant decisioning"),
            SystemSetting(key="max_dti_ceiling", value="50.00", category="decision_engine", description="Maximum debt-to-income ratio threshold for automatic approval"),
        ]
        db.add_all(settings_seed)

        # 4. Create Loan Products
        prod_standard_id = uuid.uuid4()
        prod_standard = LoanProduct(
            id=prod_standard_id,
            tenant_id=tenant_id,
            code="PERSONAL_STANDARD",
            name="Standard Personal Loan",
            description="Flexible online personal loans for working citizens across PNG.",
            min_amount=200,
            max_amount=15000,
            interest_rate_bp=1500, # 15%
            min_term=2,
            max_term=26,
            compounding_period="fortnightly",
            admin_fee=50,
            late_fee_bp=500,
            min_income=300,
            max_dti_pct=50.00,
            is_active=True,
        )

        prod_public_servant_id = uuid.uuid4()
        prod_public_servant = LoanProduct(
            id=prod_public_servant_id,
            tenant_id=tenant_id,
            code="PUBLIC_SERVANT_ALESCO",
            name="Public Servant Payroll Loan",
            description="Low-interest salary deduction loans for PNG public servants governed by Alesco 50% net pay retention rules.",
            min_amount=500,
            max_amount=50000,
            interest_rate_bp=1000, # 10%
            min_term=4,
            max_term=52,
            compounding_period="fortnightly",
            admin_fee=30,
            late_fee_bp=300,
            min_income=500,
            max_dti_pct=50.00,
            is_active=True,
        )

        db.add_all([prod_standard, prod_public_servant])

        # 5. Seed Customer 1: Kila Kopi (Public Servant)
        u_kila_id = uuid.uuid4()
        u_kila = User(
            id=u_kila_id,
            tenant_id=tenant_id,
            email="kila.kopi@gov.pg",
            password_hash=hash_password("password123"),
            role="customer",
            full_name="Kila Kopi",
            is_active=True,
        )
        db.add(u_kila)

        c_kila_id = uuid.uuid4()
        c_kila = Customer(
            id=c_kila_id,
            tenant_id=tenant_id,
            user_id=u_kila_id,
            phone_hash=hash_phone("67570001111"),
            national_id_hash=hash_phone("PNG-NID-100293"),
            encrypted_full_name=encrypt_field("Kila Kopi"),
            encrypted_address=encrypt_field("Waigani, Port Moresby, NCD"),
            encrypted_employer=encrypt_field("Department of Treasury"),
            is_public_servant=True,
            alesco_file_number="EMP-98765",
            status="active",
            risk_flag="none",
        )
        db.add(c_kila)

        db.add(CustomerProfile(
            customer_id=c_kila_id,
            date_of_birth=date(1988, 5, 12),
            gender="Male",
            marital_status="Married",
            dependents_count=2,
            residential_status="Renting",
            province="National Capital District",
            district="Moresby North-West",
            ward="Waigani 4",
        ))

        db.add(EmploymentRecord(
            customer_id=c_kila_id,
            employer_name="Department of Treasury",
            position="Senior Finance Officer",
            employment_type="full_time",
            start_date=date(2018, 3, 1),
            pay_frequency="fortnightly",
            alesco_number="EMP-98765",
        ))

        db.add(IncomeRecord(
            customer_id=c_kila_id,
            gross_income_fortnightly=2800.0,
            net_income_fortnightly=1950.0,
            secondary_income=0.0,
            verified=True,
        ))

        db.add(BankAccount(
            customer_id=c_kila_id,
            bank_name="Bank South Pacific (BSP)",
            account_number_hash=hash_phone("1002938475"),
            account_name="Kila Kopi",
            bsb_code="089001",
            is_primary=True,
            verified=True,
        ))

        db.add(RiskProfile(
            customer_id=c_kila_id,
            risk_tier="low",
            risk_score=780,
            max_approved_limit=20000.00,
        ))

        # Seed Loan Application & Active Loan for Kila
        app_kila_id = uuid.uuid4()
        app_kila = LoanApplication(
            id=app_kila_id,
            tenant_id=tenant_id,
            customer_id=c_kila_id,
            loan_product_id=prod_public_servant_id,
            amount_requested=12000.0,
            term_requested=10,
            compounding_period="fortnightly",
            purpose="Home Improvements and Family School Fees",
            step_completed=17,
            status="disbursed",
        )
        db.add(app_kila)

        offer_kila_id = uuid.uuid4()
        offer_kila = LoanOffer(
            id=offer_kila_id,
            application_id=app_kila_id,
            customer_id=c_kila_id,
            loan_product_id=prod_public_servant_id,
            approved_amount=12000.0,
            interest_rate_bp=1000,
            term_periods=10,
            compounding_period="fortnightly",
            periodic_repayment=1320.0,
            total_repayment=13200.0,
            total_interest=1200.0,
            fees=50.0,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            status="accepted",
        )
        db.add(offer_kila)

        loan_kila_id = uuid.uuid4()
        loan_kila = Loan(
            id=loan_kila_id,
            tenant_id=tenant_id,
            customer_id=c_kila_id,
            application_id=app_kila_id,
            offer_id=offer_kila_id,
            loan_product_id=prod_public_servant_id,
            principal_amount=12000.0,
            interest_rate_bp=1000,
            compounding_period="fortnightly",
            term_periods=10,
            periodic_repayment=1320.0,
            total_repayment=13200.0,
            disbursed_at=datetime.now(timezone.utc) - timedelta(days=30),
            due_at=datetime.now(timezone.utc) + timedelta(days=110),
            outstanding_balance=10500.0,
            status="active",
            net_pay_at_disbursement=1950.0,
            total_deduction_pct_at_disbursement=38.5,
        )
        db.add(loan_kila)

        # Schedules for Kila
        for i in range(1, 11):
            s_date = (datetime.now(timezone.utc) - timedelta(days=30) + timedelta(days=14*i)).date()
            p_status = "paid" if i <= 2 else "pending"
            p_amt = 1320.0 if i <= 2 else 0.0
            db.add(LoanSchedule(
                loan_id=loan_kila_id,
                instalment_number=i,
                due_date=s_date,
                principal_due=1200.0,
                interest_due=120.0,
                fee_due=0.0,
                total_due=1320.0,
                paid_amount=p_amt,
                status=p_status,
            ))

        # Ledger entries for Kila
        db.add(Transaction(
            tenant_id=tenant_id,
            loan_id=loan_kila_id,
            type="disbursement",
            amount=12000.0,
            balance_after=12000.0,
            payload_signature="SYSTEM_DISBURSED",
            notes="Initial online disbursement to BSP Account ***8475",
            idempotency_key=f"DISB-{loan_kila_id}",
        ))

        db.add(Transaction(
            tenant_id=tenant_id,
            loan_id=loan_kila_id,
            type="repayment",
            amount=1500.0,
            balance_after=10500.0,
            payload_signature="BSP_PAYMENT_CALLBACK",
            notes="BSP Online Salary Deduction Repayment",
            idempotency_key=f"PAY-{uuid.uuid4()}",
        ))

        db.add(Collection(
            loan_id=loan_kila_id,
            customer_id=c_kila_id,
            stage="current",
            days_overdue=0,
            amount_overdue=0,
            notes="Account in good standing with payroll deduction.",
        ))

        # Seed Customer 2: Manu Vani (Private Sector)
        u_manu_id = uuid.uuid4()
        u_manu = User(
            id=u_manu_id,
            tenant_id=tenant_id,
            email="manu.vani@gmail.com",
            password_hash=hash_password("password123"),
            role="customer",
            full_name="Manu Vani",
            is_active=True,
        )
        db.add(u_manu)

        c_manu_id = uuid.uuid4()
        c_manu = Customer(
            id=c_manu_id,
            tenant_id=tenant_id,
            user_id=u_manu_id,
            phone_hash=hash_phone("67570002222"),
            national_id_hash=hash_phone("PNG-NID-993812"),
            encrypted_full_name=encrypt_field("Manu Vani"),
            encrypted_address=encrypt_field("Gordons 5, Port Moresby"),
            encrypted_employer=encrypt_field("MSME Logistics PNG"),
            is_public_servant=False,
            status="active",
            risk_flag="watch",
        )
        db.add(c_manu)

        db.add(RiskProfile(
            customer_id=c_manu_id,
            risk_tier="watch",
            risk_score=620,
            max_approved_limit=5000.00,
            watch_reasons="10 days late on previous repayment",
        ))

        loan_manu_id = uuid.uuid4()
        loan_manu = Loan(
            id=loan_manu_id,
            tenant_id=tenant_id,
            customer_id=c_manu_id,
            principal_amount=4500.0,
            interest_rate_bp=1500,
            compounding_period="fortnightly",
            term_periods=6,
            periodic_repayment=862.5,
            total_repayment=5175.0,
            disbursed_at=datetime.now(timezone.utc) - timedelta(days=20),
            due_at=datetime.now(timezone.utc) - timedelta(days=6),
            outstanding_balance=3500.0,
            status="active",
        )
        db.add(loan_manu)

        db.add(Collection(
            loan_id=loan_manu_id,
            customer_id=c_manu_id,
            stage="overdue_1_7",
            days_overdue=6,
            amount_overdue=862.5,
            notes="Automated SMS reminder sent on day 3 overdue.",
        ))

        # Seed Audit Logs
        db.add(AuditLog(
            user_id=admin_user_id,
            action="SYSTEM_INIT",
            entity_type="SYSTEM",
            entity_id="SPARKLE_SYSTEM",
            payload={"message": "Sparkle Consultants Online Lending Platform initialized successfully."},
        ))

        await db.commit()
        print("Sparkle Consultants database seeding completed successfully!")
