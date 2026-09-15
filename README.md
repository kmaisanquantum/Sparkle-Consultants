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
- **Default Initial Password**: `kilomike@2024` (Configured via `seed_admin_password` setting, must be changed or overridden in production).
- **Environment Override**: The `SEED_ADMIN_PASSWORD` environment variable overrides the default initial password.

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
SEED_ADMIN_PASSWORD=kilomike@2024 PYTHONPATH=. uvicorn app.main:app --reload

# Run Pytest
PYTHONPATH=backend python3 -m pytest

# Frontend
cd frontend
npm install
npm run dev
```

## Deploying on Coolify / Single-Container Production Setup

The application deploys as a **SINGLE service** on port 8000, bundling the built React frontend directly into the Python backend container (serving the SPA via FastAPI).

### Domain Configuration (`sparcons.com` vs `www.sparcons.com`)

To ensure both apex (`sparcons.com`) and www (`www.sparcons.com`) resolve properly with automatic Let's Encrypt SSL certificates under Coolify:

1. **DNS Settings (Domain Registrar / Cloudflare):**
   - **A Record:** `sparcons.com` -> IP address of your VPS/Coolify server.
   - **CNAME Record:** `www.sparcons.com` -> `sparcons.com` (or A record pointing to the same server IP).

2. **Coolify FQDN Settings:**
   - In your service configuration under **Domains / FQDN**, set the value as comma-separated URLs:
     `https://sparcons.com, https://www.sparcons.com`
   - Coolify / Traefik will automatically generate and renew SSL certificates for both domains.

### Required Environment Variables

Set the following environment variables in your deployment environment (Coolify / Docker):

| Variable | Description | Example / Note |
| --- | --- | --- |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://wantok:secret@postgres:5432/wantok_lender` |
| `SEED_ADMIN_PASSWORD` | Initial password for `admin@dspng.tech` | `kilomike@2024` (Change after first login) |
| `HASH_PEPPER` | Secret pepper string for phone & NID hashing | Secret 32+ character random string |
| `FIELD_ENCRYPTION_KEY` | 32-byte AES-GCM encryption key | URL-safe base64 key or 32-byte secret |
| `JWT_SECRET` | Secret key for signing JWT tokens | High-entropy secret string |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins list (JSON string or comma-separated) | `["https://sparcons.com", "https://www.sparcons.com"]` |
| `BSP_MERCHANT_ID` | BSP payment gateway merchant ID | Optional / Sandbox default supplied |
| `BSP_API_KEY` | BSP payment gateway secret key | Optional |
| `SMTP_HOST` | SMTP server host for email notifications | Optional (e.g. `smtp.sendgrid.net`) |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USER` | SMTP username | Optional |
| `SMTP_PASSWORD` | SMTP password | Optional |

3. Deploy the single-container instance on port 8000.
