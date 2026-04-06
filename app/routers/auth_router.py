import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from google.oauth2 import id_token
from google.auth.transport import requests

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_otp,
)
from app.dependencies.db import get_db
from app.models.refresh_token_model import RefreshSession
from app.models.user_table_model import UserTableClass
from app.schemas.user_schemas import UserCreate, OTPVerify
from app.schemas.auth_schemas import UserLogin, ForgotPasswordRequest, ResetPasswordRequest
from app.utils.email_service import send_otp_email


router = APIRouter(prefix="/authentication", tags=["Authentication"])

CLIENT_ID = os.getenv("CLIENT_ID")






async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(UserTableClass).where(UserTableClass.email == email.lower())
    )
    return result.scalar_one_or_none()


async def create_refresh_session(db: AsyncSession, user: UserTableClass, refresh_token: str):
    token_data = decode_refresh_token(refresh_token)

    if not token_data.jti or token_data.exp is None:
        raise HTTPException(status_code=401, detail="Invalid refresh token payload")

    expires_at = datetime.fromtimestamp(token_data.exp, tz=timezone.utc).replace(tzinfo=None)

    session = RefreshSession(
        user_id=user.id,
        jti=token_data.jti,
        expires_at=expires_at,
        is_revoked=False,
    )
    db.add(session)
    await db.commit()


async def issue_tokens(db: AsyncSession, user: UserTableClass):
    payload = {
        "user_id": str( user.id),
        "email": user.email,
        "name": user.name,
        "role": user.role or "user",
    }

    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    await create_refresh_session(db, user, refresh_token)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    email = user.email.lower().strip()

    existing = await get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    if not user.password:
        raise HTTPException(status_code=400, detail="Password required")

   
    now = datetime.utcnow()
    new_user = UserTableClass(
        role="user",
        name=user.name.strip(),
        email=email,
        password=hash_password(user.password),
        provider="local",
        is_active=True,
        is_verified=False,
        created_at=now,
        updated_at=now,
    )

    db.add(new_user)
    await db.flush()

    new_user.user_id = f"AFA{new_user.id:02d}"

    otp = generate_otp()
    new_user.otp_code = otp
    new_user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)

    await db.commit()
    await send_otp_email(new_user.email, otp)

    return {
        "success": True,
        "message": "OTP sent to your email"
    }


@router.post("/verify-otp")
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, data.email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.otp_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if not user.otp_expiry or datetime.utcnow() > user.otp_expiry:
        raise HTTPException(status_code=400, detail="OTP expired")

    user.is_active = True
    user.is_verified = True
    user.otp_code = None
    user.otp_expiry = None
    user.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "message": "OTP verified successfully"
    }


@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, data.email.lower())

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before login")

    if not user.password or not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return await issue_tokens(db, user)


@router.post("/google")
async def google_login(data: dict, db: AsyncSession = Depends(get_db)):
    if not CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google login not configured")

    try:
        idinfo = id_token.verify_oauth2_token(
            data["token"],
            requests.Request(),
            CLIENT_ID
        )

        email = idinfo.get("email")
        name = idinfo.get("name") or "Google User"

        if not email:
            raise HTTPException(status_code=400, detail="Email not available")

        user = await get_user_by_email(db, email)

        if not user:
            now = datetime.utcnow()
            user = UserTableClass(
                role="user",
                name=name,
                email=email.lower(),
                password=None,
                provider="google",
                is_active=True,
                is_verified=True,
                created_at=now,
                updated_at=now,
            )
            db.add(user)
            await db.flush()
            user.user_id = f"AFA{user.id:02d}"
            await db.commit()
            await db.refresh(user)

        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is deactivated")

        if not user.is_verified:
            user.is_verified = True
            await db.commit()

        return await issue_tokens(db, user)

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Google token")


@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    token_data = decode_refresh_token(refresh_token)

    if not token_data.user_id or not token_data.email or not token_data.jti:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(RefreshSession).where(
            RefreshSession.user_id == token_data.user_id,
            RefreshSession.jti == token_data.jti,
            RefreshSession.is_revoked == False,
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=401, detail="Refresh token not recognized")

    if session.expires_at < datetime.utcnow():
        session.is_revoked = True
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = await db.get(UserTableClass, token_data.user_id)

    if not user or user.email.lower() != token_data.email.lower():
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="User not verified")

    session.is_revoked = True
    await db.commit()

    return await issue_tokens(db, user)


@router.post("/logout")
async def logout(
    refresh_token: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        token_data = decode_refresh_token(refresh_token)

        if token_data.user_id and token_data.jti:
            result = await db.execute(
                select(RefreshSession).where(
                    RefreshSession.user_id == token_data.user_id,
                    RefreshSession.jti == token_data.jti,
                    RefreshSession.is_revoked == False,
                )
            )
            session = result.scalar_one_or_none()
            if session:
                session.is_revoked = True
                await db.commit()

    except Exception:
        pass

    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.post("/resend-otp")
async def resend_otp(email: str, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, email)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_verified:
        raise HTTPException(status_code=400, detail="User already verified")

    otp = generate_otp()
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    user.updated_at = datetime.utcnow()

    await db.commit()
    await send_otp_email(user.email, otp)

    return {
        "success": True,
        "message": "OTP resent"
    }


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, data.email.lower())

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    otp = generate_otp()
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)
    user.updated_at = datetime.utcnow()

    await db.commit()
    await send_otp_email(user.email, otp)

    return {
        "success": True,
        "message": "OTP sent for password reset"
    }


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    user = await get_user_by_email(db, data.email.lower())

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.otp_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if not user.otp_expiry or user.otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    user.password = hash_password(data.new_password)
    user.otp_code = None
    user.otp_expiry = None
    user.updated_at = datetime.utcnow()

    await db.commit()

    return {
        "success": True,
        "message": "Password reset successful"
    }
