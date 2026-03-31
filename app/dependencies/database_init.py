import asyncio
from app.models.user_table_model import UserTableClass, PersonalDetailsClass
from app.models.feature_model import Feature
from app.models.transaction_model import Transaction
from app.models.category_model import Category
from app.models.budget_model import Budget
from app.models.media_model import MediaAsset

from app.dependencies.database import Base, engine


# -----------------------------------------------------------------------------------


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__main__":
    asyncio.run(init_db())