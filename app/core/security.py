from datetime import datetime, timedelta, timezone
from typing import Any
import os ,uuid , hmac
import secrets

from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel
from passlib.context import CryptContext
from fastapi import HTTPException, status

ENV = os.getenv("ENV", "local")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if ENV == "production":
        raise RuntimeError("SECRET_KEY is required in production")
    SECRET_KEY = "dev-secret-key-change-in-production"

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 2
REFRESH_TOKEN_EXPIRE_HOURS = 6

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

class TokenData(BaseModel):
    email: str | None = None
    name: str | None = None
    role: str | None = None
    user_id: str | None = None
    jti: str | None = None
    exp: int | None = None


def hash_password(password: str) -> str:
    return pwd_context.hash(password)



def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False

def generate_otp() -> str:
    return str(secrets.randbelow(900000) + 100000)

def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    if not hashed_otp:
        return False
    try:
        return pwd_context.verify(plain_otp, hashed_otp)
    except Exception:
        return False


def _build_token_payload(data: dict[str, Any], expires_delta: timedelta, token_type: str) -> dict[str, Any]:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    to_encode.update({
        "exp": expire,
        "iat": now,
        "type": token_type,
        "jti": str(uuid.uuid4())
    })
    return to_encode


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    expires_delta = expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    payload = _build_token_payload(data, expires_delta, "access")
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta | None = None) -> str:
    expires_delta = expires_delta or timedelta(hours=REFRESH_TOKEN_EXPIRE_HOURS)
    payload = _build_token_payload(data, expires_delta, "refresh")
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token_by_type(token: str, expected_type: str) -> TokenData:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        token_type = payload.get("type")
        if token_type != expected_type:
            if expected_type == "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )

        return TokenData(
            email=payload.get("email")  ,      
            name=payload.get("name"),
            role=payload.get("role"),
            user_id=payload.get("user_id"),
            jti=payload.get("jti"),
            exp=payload.get("exp"),
        )

    except ExpiredSignatureError:
        if expected_type == "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired"
        )

    except JWTError:
        if expected_type == "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


def decode_token(token: str) -> TokenData:
    return _decode_token_by_type(token, "access")


def decode_refresh_token(token: str) -> TokenData:
    return _decode_token_by_type(token, "refresh")
