"""Auth API routes: register, login, logout, me, verify-otp, resend-otp."""

import secrets
from fastapi import APIRouter, Depends, HTTPException, Response, status, Request
from pydantic import BaseModel, Field
from sqlmodel import Session as SQLSession, select

from app.core.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.core.database import User, get_session
from app.services.redis_client import redis_client
from app.services.email_service import send_otp_email
from app.services.rate_limiter import is_rate_limited

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_otp_memory_store = {}



class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str | None = Field(default=None, max_length=255)
    company_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyOTPRequest(BaseModel):
    email: str
    otp: str


class ResendOTPRequest(BaseModel):
    email: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    company_name: str | None = None
    plan: str
    subscription_status: str
    monthly_pageview_limit: int


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class MessageResponse(BaseModel):
    detail: str


@router.post("/register", response_model=MessageResponse)
async def register(body: RegisterRequest, request: Request, session: SQLSession = Depends(get_session)):
    # Rate limit: Max 5 registration attempts per 5 minutes per IP
    if await is_rate_limited(request, "auth_register", limit=5, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")

    # Server-side password strength check (enforce minimum length)
    if not body.password or len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    existing = session.exec(select(User).where(User.email == body.email)).first()
    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=409, detail="Email already registered")
        # Existing but unverified: update password in case they changed it
        existing.password_hash = hash_password(body.password)
        existing.full_name = body.full_name.strip() if body.full_name else None
        existing.company_name = body.company_name.strip() if body.company_name else None
        session.add(existing)
        session.commit()
    else:
        # Create unverified user
        user = User(
            email=body.email,
            password_hash=hash_password(body.password),
            full_name=body.full_name.strip() if body.full_name else None,
            company_name=body.company_name.strip() if body.company_name else None,
            is_verified=False,
        )
        session.add(user)
        session.commit()

    # Generate a six-digit OTP with a cryptographically secure source.
    otp = f"{secrets.randbelow(900000) + 100000}"

    # Save OTP to Redis (or in-memory fallback)
    try:
        await redis_client.set(f"otp:{body.email}", otp, ex=300)
    except Exception as e:
        import logging, time
        logging.warning(f"Redis unavailable for OTP set: {e}")
        _otp_memory_store[body.email] = (otp, time.time() + 300)

    # Send email (prints to console in development)
    send_otp_email(body.email, otp)

    return MessageResponse(detail="Verification OTP sent to email")


@router.post("/verify-otp", response_model=TokenResponse)
async def verify_otp(body: VerifyOTPRequest, request: Request, response: Response, session: SQLSession = Depends(get_session)):
    # Rate limit: Max 10 OTP validation attempts per 1 minute per IP (prevents brute forcing)
    if await is_rate_limited(request, "auth_verify_otp", limit=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many verification attempts. Please try again later.")

    user = session.exec(select(User).where(User.email == body.email)).first()
    # Do not reveal whether the user exists to prevent user enumeration. If the
    # user is not found, continue to OTP checks so the response is the same as
    # for an invalid/expired OTP.

    # Check OTP in Redis or memory store
    stored_otp = None
    try:
        stored_otp = await redis_client.get(f"otp:{body.email}")
    except Exception as e:
        import logging
        logging.warning(f"Redis unavailable for OTP get: {e}")

    if not stored_otp:
        import time
        mem_item = _otp_memory_store.get(body.email)
        if mem_item:
            code, expires_at = mem_item
            if time.time() < expires_at:
                stored_otp = code
            else:
                _otp_memory_store.pop(body.email, None)

    if not stored_otp or not user:
        raise HTTPException(status_code=400, detail="OTP expired or not found")

    if stored_otp != body.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    # Mark user as verified
    user.is_verified = True
    session.add(user)
    session.commit()
    session.refresh(user)

    # Delete OTP from Redis / memory store
    try:
        await redis_client.delete(f"otp:{body.email}")
    except Exception:
        pass
    _otp_memory_store.pop(body.email, None)

    # Generate access token
    token = create_access_token(user.id, user.email)

    # Also set HTTP-only cookie for browser convenience
    response.set_cookie(
        key="luminary_token",
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=86400,
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            plan=user.plan,
            subscription_status=user.subscription_status or "active",
            monthly_pageview_limit=user.monthly_pageview_limit,
        ),
    )


@router.post("/resend-otp", response_model=MessageResponse)
async def resend_otp(body: ResendOTPRequest, request: Request, session: SQLSession = Depends(get_session)):
    # Rate limit: Max 3 OTP resends per 5 minutes per IP
    if await is_rate_limited(request, "auth_resend_otp", limit=3, window_seconds=300):
        raise HTTPException(status_code=429, detail="Too many resend attempts. Please try again later.")

    user = session.exec(select(User).where(User.email == body.email)).first()
    # Do not reveal whether the user exists or whether the email is already
    # verified to prevent user enumeration. If the user does not exist or is
    # already verified, pretend a resend succeeded.
    if not user or user.is_verified:
        return MessageResponse(detail="If an account with that email exists, a verification email was sent")

    # Generate new OTP
    otp = f"{secrets.randbelow(900000) + 100000}"
    try:
        await redis_client.set(f"otp:{body.email}", otp, ex=300)
    except Exception as e:
        import logging, time
        logging.warning(f"Redis unavailable for resend OTP: {e}")
        _otp_memory_store[body.email] = (otp, time.time() + 300)

    send_otp_email(body.email, otp)

    return MessageResponse(detail="Verification OTP resent successfully")



@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, response: Response, session: SQLSession = Depends(get_session)):
    # Rate limit: Max 10 login attempts per 1 minute per IP
    if await is_rate_limited(request, "auth_login", limit=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many login attempts. Please try again later.")

    user = session.exec(select(User).where(User.email == body.email)).first()
    if not user or not verify_password(body.password, user.password_hash):
        # Generic error to avoid user enumeration
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email verification required")

    token = create_access_token(user.id, user.email)

    # Also set HTTP-only cookie for browser convenience
    response.set_cookie(
        key="luminary_token",
        value=token,
        httponly=True,
        samesite="none",
        secure=True,
        max_age=86400,
    )

    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            company_name=user.company_name,
            plan=user.plan,
            subscription_status=user.subscription_status or "active",
            monthly_pageview_limit=user.monthly_pageview_limit,
        ),
    )


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("luminary_token")
    return {"detail": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        company_name=user.company_name,
        plan=user.plan,
        subscription_status=user.subscription_status or "active",
        monthly_pageview_limit=user.monthly_pageview_limit,
    )
