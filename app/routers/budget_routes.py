# from fastapi import APIRouter, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.dependencies.db import get_db 
# router = APIRouter(prefix="/budgets", tags=["Budget"])


# @router.post("/")
# async def create_budget(data: dict, db: AsyncSession = Depends(get_db)):
#     return await crud.create_budget(
#         db,
#         user_id=data["user_id"],
#         name=data["name"],
#         target_amount=data["target_amount"],
#         duration_days=data["duration_days"],
#     )


# @router.get("/{user_id}")
# async def get_budgets(user_id: int, db: AsyncSession = Depends(get_db)):
#     return await crud.get_budgets(db, user_id)


# @router.put("/{budget_id}")
# async def update_budget(budget_id: int, data: dict, db: AsyncSession = Depends(get_db)):
#     return await crud.update_budget(
#         db,
#         budget_id,
#         data["user_id"],
#         data["name"],
#         data["target_amount"],
#         data["duration_days"],
#     )


# @router.delete("/{budget_id}")
# async def delete_budget(budget_id: int, user_id: int, db: AsyncSession = Depends(get_db)):
#     return await crud.delete_budget(db, budget_id, user_id)