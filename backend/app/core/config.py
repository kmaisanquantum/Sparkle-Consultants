"""
Central configuration. All values are overridden via environment
variables in production (Coolify injects these at deploy time) —
nothing sensitive is hardcoded.
"""
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://wantok:wantok@localhost:5432/wantok_lender"

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        if not isinstance(v, str):
            return v
        if v.startswith("postgres://"):
            return "postgresql+asyncpg://" + v[len("postgres://"):]
        if v.startswith("postgresql://"):
            return "postgresql+asyncpg://" + v[len("postgresql://"):]
        return v

    # CORS settings
    cors_allowed_origins_raw: str = "https://www.sparcons.com,http://localhost:3000,http://localhost:5173,http://localhost:8000"

    @property
    def cors_allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.cors_allowed_origins_raw.split(",") if origin.strip()]

    # Pepper used alongside per-record salts when hashing phone/ID numbers.
    hash_pepper: str = "CHANGE_ME_IN_PRODUCTION"

    # Symmetric key (32-byte, base64) for application-layer encryption
    # of borrower PII fields (name, address, employer).
    field_encryption_key: str = "CHANGE_ME_32_BYTE_BASE64_KEY_HERE=="

    # JWT signing for tenant/agent auth
    jwt_secret: str = "CHANGE_ME_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60 * 12

    # Regulatory ceiling: PNG Alesco public-service payroll deduction cap.
    alesco_max_total_deduction_pct: float = 50.00

    max_upload_mb: int = 8

    # Email / SMTP configuration
    smtp_server: str = "smtp.mailtrap.io"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@sparkleconsultants.com"

    # SMS Provider configuration
    sms_provider_url: str = "https://api.sms-gateway-stub.pg/v1/send"
    sms_provider_api_key: str = ""


settings = Settings()
