from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password

from app.core.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)


from datetime import datetime, timedelta
from app.core.security import generate_otp,decode_refresh_token
from fastapi.security import OAuth2PasswordRequestForm

from app.services import user
from app.utils.email_service import send_otp_email

from app.services.user import get_user_by_email, create_user
from app.dependencies.db import get_db

from google.oauth2 import id_token
from google.auth.transport import requests

from app.schemas.user_schemas import UserCreate, OTPVerify
from app.schemas.auth_schemas import UserLogin, ForgotPasswordRequest, ResetPasswordRequest

router = APIRouter(prefix="/authentication", tags=["Authentication"])

# 🔐 Used refresh tokens (basic blacklist)
REFRESH_TOKEN_BLACKLIST = set()

# 🔑 Google Client ID
CLIENT_ID = "760648200997-qn0crdqlfjjve86hh6f54f0na48e11mr.apps.googleusercontent.com"


# =========================================================
# 🔹 REGISTER
# =========================================================
@router.post("/register")
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):

    # Check existing user
    if await get_user_by_email(db, user.email):
        raise HTTPException(status_code=400, detail="User already exists")

    # Create user
    new_user = await create_user(
        db,
        user.name,
        user.email,
        user.password,
        "local"
    )

    # ✅ commit first to get ID
    await db.commit()
    await db.refresh(new_user)

    # ✅ Now generate user_id
    new_user.user_id = f"AFA{new_user.id:02d}"

    # Generate OTP
    otp = generate_otp()
    new_user.otp_code = otp
    new_user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)

    await db.commit()

    # Send OTP
    send_otp_email(new_user.email, otp)

    return {
        "success": True,
        "message": "OTP sent to your email"
    }

# =========================================================
# 🔹 VERIFY OTP
# =========================================================
@router.post("/verify-otp")
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):

    user = await get_user_by_email(db, data.email.lower())

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.otp_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if user.otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    # ✅ SUCCESS
    user.is_verified = True
    user.otp_code = None
    user.otp_expiry = None

    await db.commit()

    return {
        "success": True,
        "message": "Email verified successfully"
    }
# =========================================================
# 🔹 LOGIN
# =========================================================
# Swagger / OAuth2 login (form-data)
# @router.post("/login")
# async def login(
#     form_data: OAuth2PasswordRequestForm = Depends(),
#     db: AsyncSession = Depends(get_db)
# ):
#     email = form_data.username
#     password = form_data.password

#     user = await get_user_by_email(db, email)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     if not user.is_verified:
#         raise HTTPException(status_code=403, detail="Please verify your email before login")
#     if not verify_password(password, user.password):
#         raise HTTPException(status_code=401, detail="Invalid password")

#     payload = {"sub": user.email, "name": user.name}
#     return {
#         "access_token": create_access_token(payload),
#         "refresh_token": create_refresh_token(payload),
#         "token_type": "bearer"
#     }





@router.post("/login")
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):

    user = await get_user_by_email(db, data.email.lower())

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")

    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before login"
        )

    # ✅ DEBUG (temporary)
    print("Entered Password:", data.password)
    print("Stored Hash:", user.password)
    print("Match:", verify_password(data.password, user.password))

    # ✅ Password check
    if not verify_password(data.password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    payload = {
        "sub": user.email,
        "name": user.name,
        "role": user.role,
        "user_id": user.user_id
    }

    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer"
    }

# =========================================================
# 🔹 GOOGLE LOGIN
# =========================================================
@router.post("/google")
async def google_login(data: dict, db: AsyncSession = Depends(get_db)):
    try:
        # Verify Google token
        idinfo = id_token.verify_oauth2_token(
            data["token"],
            requests.Request(),
            CLIENT_ID
        )

        email = idinfo.get("email")
        name = idinfo.get("name")

        if not email:
            raise HTTPException(status_code=400, detail="Email not available")

        # Check user
        user = await get_user_by_email(db, email)

        if not user:
            user = await create_user(db, name, email, None, "google")

        # Auto verify Google users
        if not user.is_verified:
            user.is_verified = True
            await db.commit()

        payload = {
            "sub": user.email,
            "name": user.name,
            "role": user.role
        }

        return {
            "access_token": create_access_token(payload),
            "refresh_token": create_refresh_token(payload),
            "token_type": "bearer"
        }

    except Exception as e:
        print("Google error:", e)
        raise HTTPException(status_code=400, detail="Invalid Google token")


# =========================================================
# 🔹 REFRESH TOKEN
# =========================================================
@router.post("/refresh")
async def refresh_token(
    refresh_token: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    if refresh_token in REFRESH_TOKEN_BLACKLIST:
        raise HTTPException(status_code=401, detail="Token already used")

    try:
        token_data = decode_refresh_token(refresh_token)
    except HTTPException as e:
        raise e

    if not token_data or not token_data.email:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = await get_user_by_email(db, token_data.email.lower())
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="User not verified")

    REFRESH_TOKEN_BLACKLIST.add(refresh_token)

    payload = {
        "sub": user.email,
        "name": user.name,
        "role": user.role,
        "user_id": user.user_id
    }

    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer"
    }

    # Check reuse
    if refresh_token in REFRESH_TOKEN_BLACKLIST:
        raise HTTPException(status_code=401, detail="Token already used")

    # Decode safely
    try:
        token_data = decode_refresh_token(refresh_token)
    except HTTPException as e:
        raise e

    if not token_data or not token_data.email:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # Blacklist old token
    REFRESH_TOKEN_BLACKLIST.add(refresh_token)

    payload = {
        "sub": token_data.email,
        "name": token_data.name,
        "role": token_data.role ,
        "user_id": token_data.user_id
    }

    return {
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer"
    }


# =========================================================
# 🔹 LOGOUT
# =========================================================
@router.post("/logout")
async def logout(refresh_token: str = Form(...)):

    if refresh_token:
        REFRESH_TOKEN_BLACKLIST.add(refresh_token)

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

    await db.commit()

    send_otp_email(user.email, otp)

    return {"message": "OTP resent"}

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):

    user = await get_user_by_email(db, data.email.lower())

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Generate OTP
    otp = generate_otp()
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=5)

    await db.commit()

    send_otp_email(user.email, otp)

    return {
        "success": True,
        "message": "OTP sent for password reset"
    }

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):

    user = await get_user_by_email(db, data.email.lower())

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check OTP
    if user.otp_code != data.otp:
        raise HTTPException(status_code=400, detail="Invalid OTP")

    if not user.otp_expiry or user.otp_expiry < datetime.utcnow():
        raise HTTPException(status_code=400, detail="OTP expired")

    # ✅ Change password
    user.password = hash_password(data.new_password)

    # Clear OTP
    user.otp_code = None
    user.otp_expiry = None

    await db.commit()

    return {
        "success": True,
        "message": "Password reset successful"
    }