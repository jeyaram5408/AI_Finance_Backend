from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.dependencies.db import get_db
from app.models.user_table_model import UserTableClass
from app.core.security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/authentication/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    token_data = decode_token(token)

    result = await db.execute(
        select(UserTableClass)
        .options(selectinload(UserTableClass.personal))
        .where(UserTableClass.email == token_data.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is deactivated")

    if not user.is_verified:
        raise HTTPException(status_code=403, detail="User not verified")

    if not token_data.email:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    return user


def require_admin(user: UserTableClass = Depends(get_current_user)):
    if not user.role or user.role.lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user
