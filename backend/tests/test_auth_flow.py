import pytest
import pyotp
from jose import jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings


def test_password_reset_jwt_token():
    expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
    reset_payload = {
        "user_id": "test-user-uuid",
        "type": "reset_password",
        "exp": int(expiry.timestamp())
    }
    token = jwt.encode(reset_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert decoded["user_id"] == "test-user-uuid"
    assert decoded["type"] == "reset_password"


def test_totp_mfa_flow():
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    token = totp.now()

    assert totp.verify(token) is True
    assert totp.verify("000000") is False
