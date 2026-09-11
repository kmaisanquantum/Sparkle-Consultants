from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import traceback
from app.core.database import engine, Base
from app.routers import (
    credit_check, payslip, sync, dashboard, auth, borrowers, loans, collateral,
    calculator, applications, offers, agreements, payments, products, customers, admin
)
from app.seed import seed_data

app = FastAPI(
    title="Sparkle Consultants API",
    description="A fully online lending service for Papua New Guinea",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        print("Error self-healing schema on startup:")
        traceback.print_exc()

    try:
        await seed_data()
    except Exception as e:
        print(f"Error seeding database: {e}")
        traceback.print_exc()

app.include_router(auth.router)
app.include_router(calculator.router)
app.include_router(applications.router)
app.include_router(offers.router)
app.include_router(agreements.router)
app.include_router(loans.router)
app.include_router(payments.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(admin.router)

# Legacy / scaffold routers retained for compatibility
app.include_router(borrowers.router)
app.include_router(collateral.router)
app.include_router(credit_check.router)
app.include_router(sync.router)
app.include_router(payslip.router)
app.include_router(dashboard.router)


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException

static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def catch_all(full_path: str):
        if full_path.startswith("api/") or full_path == "healthz":
            raise HTTPException(status_code=404, detail="Not Found")

        file_path = os.path.join(static_dir, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)

        return FileResponse(os.path.join(static_dir, "index.html"))
