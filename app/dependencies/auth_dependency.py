from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import decode_token
from app.dependencies.db import get_db
from app.models.user_table_model import UserTableClass

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/authentication/login")


def normalize_role(role: str | None) -> str:
    return (role or "user").strip().lower()


def is_admin(user: UserTableClass) -> bool:
    return normalize_role(user.role) == "admin"


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserTableClass:
    token_data = decode_token(token)

    if not token_data.email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    result = await db.execute(
        select(UserTableClass)
        .options(
            selectinload(UserTableClass.personal),
            selectinload(UserTableClass.settings),
        )
        .where(UserTableClass.email == token_data.email.lower())
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is deactivated"
        )

    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User not verified"
        )

    return user


async def require_admin(
    current_user: UserTableClass = Depends(get_current_user),
) -> UserTableClass:
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only"
        )
    return current_user


def require_roles(*allowed_roles: str) -> Callable:
    allowed = {role.strip().lower() for role in allowed_roles if role}

    async def checker(
        current_user: UserTableClass = Depends(get_current_user),
    ) -> UserTableClass:
        if normalize_role(current_user.role) not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user

    return checker


def ensure_self_or_admin(current_user: UserTableClass, target_user_id: int) -> None:
    if current_user.id != target_user_id and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own data"
        )
