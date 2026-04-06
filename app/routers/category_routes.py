from typing import List

from fastapi import APIRouter, Depends 
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user

from app.schemas.category_schema import CategoryCreate, CategoryResponse,CategoryUpdate
from app.services import category_crud as crud

from app.dependencies.auth_dependency import require_admin
from app.models.user_table_model import UserTableClass

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryResponse)
async def create_category(
    data: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await crud.create_category(db, data, current_user)

@router.get("", response_model=List[CategoryResponse])
async def get_all_categories(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await crud.get_categories(db, current_user.id)

# ✅ DELETE
@router.delete("/{cat_id}")
async def delete_category(
    cat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await crud.delete_category(db, cat_id, current_user.id)


# ✅ UPDATE
@router.patch("/{cat_id}", response_model=CategoryResponse)
async def update_category(
    cat_id: int,
    data: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await crud.update_category(db, cat_id, data, current_user.id)