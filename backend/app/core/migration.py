import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from app.models.orm import Base

logger = logging.getLogger("sparkle_api")

# Map SQLAlchemy column types / defaults to PostgreSQL DDLS for idempotent ADD COLUMN IF NOT EXISTS
# This self-heals schema drift on existing databases when new columns are added to ORM models.
SELF_HEAL_COLUMNS = [
    # Table: users
    ("users", "mfa_enabled", "BOOLEAN NOT NULL DEFAULT false"),
    ("users", "mfa_secret", "TEXT NULL"),
    ("users", "role", "VARCHAR NOT NULL DEFAULT 'customer'"),
    ("users", "full_name", "TEXT NOT NULL DEFAULT ''"),
    ("users", "is_active", "BOOLEAN NOT NULL DEFAULT true"),

    # Table: audit_logs
    ("audit_logs", "user_id", "UUID NULL"),
    ("audit_logs", "customer_id", "UUID NULL"),
    ("audit_logs", "action", "TEXT NOT NULL DEFAULT 'UNKNOWN'"),
    ("audit_logs", "entity_type", "TEXT NOT NULL DEFAULT 'SYSTEM'"),
    ("audit_logs", "entity_id", "TEXT NULL"),
    ("audit_logs", "payload", "JSONB NULL"),
    ("audit_logs", "ip_address", "TEXT NULL"),
    ("audit_logs", "timestamp", "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"),

    # Table: system_settings
    ("system_settings", "category", "TEXT NOT NULL DEFAULT 'general'"),
    ("system_settings", "description", "TEXT NULL"),

    # Table: loan_products
    ("loan_products", "min_income", "NUMERIC(14, 2) NOT NULL DEFAULT 500"),
    ("loan_products", "max_dti_pct", "NUMERIC(5, 2) NOT NULL DEFAULT 50.00"),
    ("loan_products", "late_fee_bp", "INTEGER NOT NULL DEFAULT 500"),
    ("loan_products", "admin_fee", "NUMERIC(14, 2) NOT NULL DEFAULT 50"),

    # Table: loan_applications
    ("loan_applications", "draft_data", "JSONB NULL"),
    ("loan_applications", "step_completed", "INTEGER NOT NULL DEFAULT 1"),

    # Table: loan_offers
    ("loan_offers", "calculation_methodology", "TEXT NOT NULL DEFAULT 'reducing_balance'"),
    ("loan_offers", "calculation_snapshot", "JSONB NULL"),

    # Table: loans
    ("loans", "net_pay_at_disbursement", "NUMERIC(14, 2) NULL"),
    ("loans", "total_deduction_pct_at_disbursement", "NUMERIC(5, 2) NULL"),
    ("loans", "calculation_methodology", "TEXT NOT NULL DEFAULT 'reducing_balance'"),
    ("loans", "calculation_snapshot", "JSONB NULL"),

    # Table: collections
    ("collections", "assigned_agent_id", "UUID NULL"),
    ("collections", "last_contact_date", "DATE NULL"),
    ("collections", "next_action_date", "DATE NULL"),
]


async def self_heal_schema(engine: AsyncEngine) -> None:
    """Executes ALTER TABLE ... ADD COLUMN IF NOT EXISTS for all known modern columns
    to ensure persistent databases do not raise UndefinedColumn errors."""
    logger.info("Running schema self-heal migration checks...")
    is_sqlite = engine.dialect.name == "sqlite"
    async with engine.begin() as conn:
        for table_name, column_name, column_def in SELF_HEAL_COLUMNS:
            try:
                if is_sqlite:
                    sq_def = column_def.replace("TIMESTAMP WITH TIME ZONE", "DATETIME").replace("JSONB", "JSON").replace("UUID", "TEXT")
                    sql = text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sq_def};")
                else:
                    sql = text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_def};")
                await conn.execute(sql)
            except Exception as e:
                logger.debug(f"Self-heal column note for {table_name}.{column_name}: {e}")
    logger.info("Schema self-heal migration checks completed successfully.")
