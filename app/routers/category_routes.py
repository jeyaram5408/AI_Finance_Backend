from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db

from app.schemas.category_schema import CategoryCreate,CategoryUpdate
from app.services import category_crud as crud


router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("/")
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
):
    return await crud.create_category(db, data)


@router.get("/")
async def get_all_categories(
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_categories(db)


@router.delete("/{cat_id}")
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await crud.delete_category(db, cat_id)

@router.patch("/{cat_id}")
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await crud.update_category(db, cat_id, data)