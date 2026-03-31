from datetime import datetime, timedelta, timezone
import os
import random
from jose import jwt, JWTError, ExpiredSignatureError
from pydantic import BaseModel
from passlib.context import CryptContext
from fastapi import HTTPException

SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-key-change-in-production"
ALGORITHM = "HS256"

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


class TokenData(BaseModel):
    email: str | None = None
    name: str | None = None
    role: str | None = None
    user_id: str | None = None


def generate_otp():
    return str(random.randint(100000, 999999))


def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=2)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(hours=6)):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")

        return TokenData(
            email=payload.get("sub"),
            name=payload.get("name"),
            role=payload.get("role"),
            user_id=payload.get("user_id"),
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def decode_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        return TokenData(
            email=payload.get("sub"),
            name=payload.get("name"),
            role=payload.get("role"),
            user_id=payload.get("user_id"),
        )
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
