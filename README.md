# Sparkle Consultants — Online Lending Platform

A fully online lending service for Papua New Guinea, operated as a single-business automated lending platform with customer self-service portal, automated credit decisioning, digital contracts, payment reconciliation, and administrative control.

## Repo layout

```
schema/               PostgreSQL multi-tenant schema (schema.sql)
backend/               FastAPI service (Python 3.12)
  app/core/            config, DB session, crypto helpers, auth deps
  app/models/          SQLAlchemy ORM models + Pydantic schemas
  app/routers/         credit-check, sync, payslip HTTP endpoints
  app/services/        credit_checker, sync_pipeline, payslip_parser
frontend/              React + Tailwind merchant/lender dashboard
docs/                  Design docs (payslip parsing pipeline, etc.)
docker-compose.yml     Coolify-ready multi-service deploy
```

## What's implemented

- **Schema**: `tenants` (with password-based authentication), `borrowers` (SHA-256-hashed identity, AES-GCM
  encrypted PII), `loans` (with Alesco ceiling snapshot fields),
  `collateral_logs`, `transactions` (idempotent, signed).
- **Authentication system**: Secure JWT-based multi-tenant authentication (`POST /api/v1/auth/login` and `GET /api/v1/auth/me`).
- **Anonymized cross-tenant credit checker**: hashes a phone/ID and
  returns only an aggregate risk tier + counts — never another
  tenant's identity or loan details.
- **Offline sync pipeline**: ingests signed batches from SQLite edge
  nodes, verifies HMAC signatures, applies atomically, and is
  idempotent on `(tenant_id, client_generated_id)` so retried uploads
  over flaky data never double-post a repayment.
- **Alesco payslip parser**: OCR + regex extraction of Gross/Net Pay
  and deduction lines, with a reconciliation check and a 50%-ceiling
  compliance check. See `docs/payslip_parsing.md`.
- **Tenant CRUD management APIs**: Fully implemented and secure routes for creating and listing borrowers, issuing loans (with compliance checks), logging/releasing physical collateral, and recording repayments.
- **Lender dashboard**: Live statistics including Total Capital Out, Expected Fortnightly Repayments, At-Risk Accounts, and Collateral Vault.

## Seeding & Demo Access

The system comes with an idempotent automatic database seeder. On startup, a demo tenant with live statistics, multiple registered borrowers, outstanding loans, and collateral logs is created.

- **Seed login email**: `owner@sparkleconsultants.com`
- **Password**: `password123`

## What you still need to add before production

- Device-secret provisioning/rotation for the sync pipeline's HMAC
  signing (currently passed in as a header per request).
- Real Alembic migrations instead of the single `schema.sql`, once the
  schema needs to evolve post-launch.

## Local development

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real secrets
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Deploying on a self-hosted VPS via Coolify / PaaS Platforms

The application deploys as a **SINGLE service** on port 8000, bundling the built React frontend directly into the Python backend container (serving the SPA via FastAPI). This eliminates cross-container CORS, 502 gateway errors, or inter-service DNS resolution issues.

### Option A: Single-Container Application Deploy (Recommended)
1. In Coolify or your deployment platform, create a **New Resource → Application**.
2. Point it at this repository with:
   - **Build Pack**: `Dockerfile` (preferred, bypasses Nixpacks entirely) OR `Nixpacks` (a root `nixpacks.toml` is provided for platforms that force Nixpacks).
   - **Base Directory**: `/` (repo root)
   - **Exposed Port**: `8000` (the single exposed port serving both API and SPA)
3. **Important for Dockerfile vs Nixpacks builds:**
   - **Dockerfile build pack (recommended):** Clear any "Nix Packages" or custom packages field in Coolify's UI entirely so it does not attempt to resolve Nix dependencies.
   - **Nixpacks build pack:** Note that Coolify's UI "Nix Packages" field overrides `nixpacks.toml`. If configured in the UI, ensure exact valid Nix package attribute names are used (e.g., `poppler_utils` with an underscore, NOT `poppler-utils`, `tesseract`, `nodejs_20`, `python312`) and avoid specifying duplicate Python packages.
4. Configure the following environment variables in your platform control panel:
   - `DATABASE_URL`: Connection string to your PostgreSQL database using the async driver, e.g., `postgresql+asyncpg://<user>:<password>@<managed-db-host>:5432/<dbname>`. (Note: ensure you set this explicitly in your panel rather than relying on the hardcoded fallback `wantok` connection string in `backend/app/core/config.py`).
   - `HASH_PEPPER`: Secret random string for identity hashing.
   - `FIELD_ENCRYPTION_KEY`: A symmetric 32-byte key encoded in base64. Generate one using:
     ```bash
     python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"
     ```
   - `JWT_SECRET`: Random secret for signing access tokens.
5. Deploy. On startup, the FastAPI app automatically runs database table migrations (`Base.metadata.create_all`) and seeds initial demo stats, making the app immediately functional.

### Option B: Multi-Service Docker Compose
1. In Coolify: **New Resource → Docker Compose**, pointing at `docker-compose.yml` at the root.
2. Set environment variables: `POSTGRES_PASSWORD`, `HASH_PEPPER`, `FIELD_ENCRYPTION_KEY`, `JWT_SECRET`, `PUBLIC_API_URL`.
3. Deploy. Coolify builds the separate `backend/` and `frontend/` directories and configures internal proxy resolution.

## Pushing to GitHub

```bash
cd wantok-lender
git init
git add .
git commit -m "Initial scaffold: schema, backend, dashboard"
git branch -M main
git remote add origin https://github.com/<your-org>/wantok-lender.git
git push -u origin main
```
