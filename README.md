# Sparkle Consultants — Online Lending Platform

A fully online lending service for Papua New Guinea, operated as a single-business automated lending platform with customer self-service portal, automated credit decisioning, digital contracts, payment reconciliation, and administrative control.

## Repo layout

```
schema/               PostgreSQL schema & immutability triggers (schema.sql)
backend/               FastAPI service (Python 3.12)
  app/core/            config, DB session, crypto helpers, auth deps
  app/models/          SQLAlchemy ORM models + Pydantic schemas
  app/routers/         auth, applications, offers, agreements, loans, payments, products, customers, admin, reports
  app/services/        credit_decision_engine, calculation_engine, notification_service, repayment_engine, agreement_service
frontend/              React + Tailwind borrower portal & admin console
docker-compose.yml     Coolify-ready multi-service deploy
```

## Seeding & Administrator Account Setup

On startup, the system seeds the initial platform administrator:
- **Admin Email**: `admin@dspng.tech`
- **Password**: Configured via the `SEED_ADMIN_PASSWORD` environment variable. If `SEED_ADMIN_PASSWORD` is not set, the seeder automatically generates a secure 16-character random password and logs it to stdout.

## Production Reliability, Monitoring & Disaster Recovery

### Database Backup & Disaster Recovery Procedures
1. **Automated Logical Backups:**
   Schedule daily `pg_dump` backups using cron or Coolify automated backup task:
   ```bash
   pg_dump -U wantok -h localhost -d wantok_lender -F c -b -v -f /backups/wantok_lender_$(date +%Y%m%m_%H%M%S).dump
   ```
2. **Point-In-Time Recovery (PITR):**
   Enable Write-Ahead Logging (`wal_level = replica`) and configure PostgreSQL WAL archiving to S3 or block storage for sub-minute disaster recovery capabilities.
3. **Database Restore Runbook:**
   To restore from a dump backup:
   ```bash
   pg_restore -U wantok -h localhost -d wantok_lender -v -c /backups/wantok_lender_target.dump
   ```

### Application Error Logging & Monitoring Setup
1. **Structured Logging:**
   The backend uses standard Python `logging` with HTTP request tracking middleware in `backend/app/main.py`. Logs capture request paths, status codes, and unhandled exception tracebacks.
2. **Health Check Endpoint:**
   Monitor uptime using `GET /healthz` which returns `{"status": "ok"}`.
3. **Sentry Error Tracking (Production Recommended):**
   Configure Sentry DSN in environment settings for real-time exception reporting.

## Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real secrets
SEED_ADMIN_PASSWORD=your_secure_password PYTHONPATH=. uvicorn app.main:app --reload

# Run Pytest
PYTHONPATH=backend python3 -m pytest

# Frontend
cd frontend
npm install
npm run dev
```

## Deploying on Coolify / Single-Container Production Setup

The application deploys as a **SINGLE service** on port 8000, bundling the built React frontend directly into the Python backend container (serving the SPA via FastAPI).

1. Set required environment variables: `DATABASE_URL`, `HASH_PEPPER`, `FIELD_ENCRYPTION_KEY`, `JWT_SECRET`, `SEED_ADMIN_PASSWORD`.
2. Access the single-container instance on port 8000.
