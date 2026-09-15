from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from jose import jwt, JWTError
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import pyotp
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.database import get_db
from app.core.crypto import hash_password, verify_password, hash_phone, encrypt_field
from app.models.orm import User, Customer, CustomerProfile, RiskProfile, Tenant, Notification
from app.services.audit_service import AuditService

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: Optional[str] = None
    username: Optional[str] = None
    password: str
    mfa_code: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str
    role: str
    full_name: str
    customer_id: Optional[str] = None


class CustomerRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: str
    national_id: Optional[str] = None
    province: Optional[str] = "National Capital District"


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    role: str
    full_name: str
    mfa_enabled: bool
    customer_id: Optional[str] = None


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class MFASetupResponse(BaseModel):
    secret: str
    provisioning_uri: str


class MFAVerifyRequest(BaseModel):
    mfa_code: str
    secret: Optional[str] = None


async def get_current_user(authorization: str = Header(...), db: AsyncSession = Depends(get_db)) -> User:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if payload.get("type") == "reset_password":
        raise HTTPException(status_code=401, detail="Reset token cannot be used for authentication")

    user_id = payload.get("user_id") or payload.get("tenant_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token missing identity claims")

    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account not found or inactive")
    return user


def require_roles(*allowed_roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        # Treats "administrator" or "owner" as super-roles if "administrator" or "admin" is in allowed_roles
        if current_user.role not in allowed_roles and current_user.role not in ("administrator", "owner"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User role '{current_user.role}' is not authorized to access this resource"
            )
        return current_user
    return role_checker


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register_customer(
    request: Request,
    body: CustomerRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    # Get or create primary single-business Tenant
    tenant_stmt = select(Tenant).limit(1)
    tenant = (await db.execute(tenant_stmt)).scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            business_name="Sparkle Consultants",
            contact_email="info@sparkleconsultants.com",
            is_active=True
        )
        db.add(tenant)
        await db.flush()

    # Check if email exists
    stmt = select(User).where(User.email == body.email.lower().strip())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="An account with this email address already exists.",
        )

    # 1. Create User with role "client" (default for new self-registrations / prospective leads before active loan conversion)
    user = User(
        tenant_id=tenant.id,
        email=body.email.lower().strip(),
        password_hash=hash_password(body.password),
        role="client",
        full_name=body.full_name,
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # 2. Create Customer with tenant_id provided
    customer = Customer(
        tenant_id=tenant.id,
        user_id=user.id,
        phone_hash=hash_phone(body.phone_number),
        national_id_hash=hash_phone(body.national_id) if body.national_id else None,
        encrypted_full_name=encrypt_field(body.full_name),
        encrypted_address=encrypt_field(body.province or ""),
        status="active",
        risk_flag="none",
    )
    db.add(customer)
    await db.flush()

    # 3. Create Profile & Risk Profile
    db.add(CustomerProfile(customer_id=customer.id, province=body.province))
    db.add(RiskProfile(customer_id=customer.id, risk_tier="low", risk_score=700, max_approved_limit=10000.00))

    # Welcome Notification
    db.add(Notification(
        user_id=user.id,
        customer_id=customer.id,
        title="Welcome to Sparkle Consultants",
        message=f"Welcome {body.full_name}! Your client account has been registered successfully.",
        channel="in_app"
    ))

    await AuditService.log_event(
        db=db,
        action="CUSTOMER_REGISTERED",
        entity_type="USER",
        entity_id=str(user.id),
        user_id=str(user.id),
        customer_id=str(customer.id),
        payload={"email": body.email, "full_name": body.full_name, "role": "client"}
    )

    await db.commit()

    # Generate JWT with user_id and tenant_id
    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {
        "user_id": str(user.id),
        "tenant_id": str(user.id),
        "role": user.role,
        "customer_id": str(customer.id),
        "exp": int(expiry.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        role=user.role,
        full_name=user.full_name,
        customer_id=str(customer.id)
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    identifier = (body.email or body.username or "").lower().strip()
    if not identifier:
        raise HTTPException(
            status_code=400,
            detail="Must provide email or username",
        )

    stmt = select(User).where(User.email == identifier)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Check MFA if enabled
    if user.mfa_enabled:
        if not body.mfa_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required for login",
            )
        totp = pyotp.TOTP(user.mfa_secret)
        if not totp.verify(body.mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid MFA code",
            )

    cust_stmt = select(Customer).where(Customer.user_id == user.id)
    cust = (await db.execute(cust_stmt)).scalar_one_or_none()
    customer_id = str(cust.id) if cust else None

    await AuditService.log_event(
        db=db,
        action="USER_LOGIN",
        entity_type="USER",
        entity_id=str(user.id),
        user_id=str(user.id),
        customer_id=customer_id
    )

    expiry = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expiry_minutes)
    payload = {
        "user_id": str(user.id),
        "tenant_id": str(user.id),
        "role": user.role,
        "customer_id": customer_id,
        "exp": int(expiry.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user_id=str(user.id),
        role=user.role,
        full_name=user.full_name,
        customer_id=customer_id
    )


@router.post("/forgot-password")
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).where(User.email == body.email.lower().strip())
    user = (await db.execute(stmt)).scalar_one_or_none()

    # Generic message to prevent email enumeration
    response_msg = {"message": "If an account with that email exists, password reset instructions have been sent."}
    if not user:
        return response_msg

    expiry = datetime.now(timezone.utc) + timedelta(minutes=15)
    reset_payload = {
        "user_id": str(user.id),
        "type": "reset_password",
        "exp": int(expiry.timestamp())
    }
    reset_token = jwt.encode(reset_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    db.add(Notification(
        user_id=user.id,
        title="Password Reset Request",
        message=f"A password reset was requested. Use reset token: {reset_token}",
        channel="in_app"
    ))

    await AuditService.log_event(
        db=db,
        action="PASSWORD_RESET_REQUESTED",
        entity_type="USER",
        entity_id=str(user.id),
        user_id=str(user.id)
    )
    await db.commit()

    return {"message": "Password reset token generated successfully", "reset_token": reset_token}


@router.post("/reset-password")
async def reset_password(
    body: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = jwt.decode(body.token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if payload.get("type") != "reset_password":
        raise HTTPException(status_code=400, detail="Invalid token type")

    user_id = payload.get("user_id")
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = hash_password(body.new_password)

    await AuditService.log_event(
        db=db,
        action="PASSWORD_RESET_COMPLETED",
        entity_type="USER",
        entity_id=str(user.id),
        user_id=str(user.id)
    )
    await db.commit()

    return {"message": "Password has been reset successfully."}


@router.post("/mfa/setup", response_model=MFASetupResponse)
async def mfa_setup(
    current_user: User = Depends(get_current_user)
):
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    provisioning_uri = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="Sparkle Consultants"
    )
    return MFASetupResponse(secret=secret, provisioning_uri=provisioning_uri)


@router.post("/mfa/verify")
async def mfa_verify(
    body: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    secret = body.secret or current_user.mfa_secret
    if not secret:
        raise HTTPException(status_code=400, detail="MFA secret missing")

    totp = pyotp.TOTP(secret)
    if not totp.verify(body.mfa_code):
        raise HTTPException(status_code=400, detail="Invalid MFA verification code")

    current_user.mfa_enabled = True
    current_user.mfa_secret = secret

    await AuditService.log_event(
        db=db,
        action="MFA_ENABLED",
        entity_type="USER",
        entity_id=str(current_user.id),
        user_id=str(current_user.id)
    )
    await db.commit()

    return {"message": "MFA enabled successfully"}


@router.post("/mfa/disable")
async def mfa_disable(
    body: MFAVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.mfa_enabled or not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled for this account")

    totp = pyotp.TOTP(current_user.mfa_secret)
    if not totp.verify(body.mfa_code):
        raise HTTPException(status_code=400, detail="Invalid MFA verification code")

    current_user.mfa_enabled = False
    current_user.mfa_secret = None

    await AuditService.log_event(
        db=db,
        action="MFA_DISABLED",
        entity_type="USER",
        entity_id=str(current_user.id),
        user_id=str(current_user.id)
    )
    await db.commit()

    return {"message": "MFA disabled successfully"}


@router.get("/me", response_model=UserMeResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cust_stmt = select(Customer).where(Customer.user_id == current_user.id)
    cust = (await db.execute(cust_stmt)).scalar_one_or_none()

    return UserMeResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        role=current_user.role,
        full_name=current_user.full_name,
        mfa_enabled=current_user.mfa_enabled,
        customer_id=str(cust.id) if cust else None
    )
