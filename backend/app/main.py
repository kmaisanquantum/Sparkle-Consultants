from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import logging
import traceback
from app.core.config import settings
from app.core.database import engine, Base
from app.routers import (
    credit_check, payslip, sync, dashboard, auth, borrowers, loans, collateral,
    calculator, applications, offers, agreements, payments, products, customers, admin, reports
)
from app.seed import seed_data

# Configure structured application logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sparkle_api")

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="Sparkle Consultants API",
    description="A fully online lending service for Papua New Guinea",
    version="0.1.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def structured_logging_and_error_middleware(request: Request, call_next):
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        logger.info(f"Completed Request: {request.method} {request.url.path} - Status {response.status_code}")
        return response
    except Exception as exc:
        logger.error(f"Unhandled Exception handling {request.method} {request.url.path}: {exc}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error", "message": "An unexpected system error occurred."}
        )


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Sparkle Consultants API service...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified and self-healed successfully.")
    except Exception as e:
        logger.error("Error self-healing schema on startup:")
        logger.error(traceback.format_exc())

    try:
        await seed_data()
        logger.info("Database seeding checked and completed successfully.")
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        logger.error(traceback.format_exc())


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
app.include_router(reports.router)

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
