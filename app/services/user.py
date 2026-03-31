from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_table_model import UserTableClass
from app.core.security import hash_password


async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(UserTableClass).where(UserTableClass.email == email.lower())
    )
    return result.scalars().first()


async def create_user(db: AsyncSession, name: str, email: str, password: str | None = None, provider: str = "local"):
    hashed = hash_password(password) if password else None
    now = datetime.utcnow()

    new_user = UserTableClass(
        role="user",
        name=name,
        email=email.lower(),
        password=hashed,
        provider=provider,
        created_at=now,
        updated_at=now,
        is_active=True,
        is_verified=False if provider == "local" else True,
    )

    db.add(new_user)
    await db.flush()

    new_user.user_id = f"AFA{new_user.id:02d}"

    await db.commit()
    await db.refresh(new_user)
    return new_user
