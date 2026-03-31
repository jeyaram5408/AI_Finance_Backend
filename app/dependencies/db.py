from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from app.dependencies.database import SessionLocal


# -----------------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with AsyncSessionLocal() as session:
#         yield session