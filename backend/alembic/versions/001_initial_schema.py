"""Initial baseline schema migration including users.mfa_enabled and users.mfa_secret

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-03-31 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Ensure users table has mfa_enabled and mfa_secret columns
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN NOT NULL DEFAULT false;")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret TEXT NULL;")

def downgrade() -> None:
    pass
