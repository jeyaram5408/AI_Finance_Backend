from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth_dependency import get_current_user, require_admin
from app.dependencies.db import get_db
from app.models.user_table_model import UserTableClass
from app.schemas.feature_schema import FeatureCreate, FeatureUpdate
from app.services import feature_crud as crud


router = APIRouter(prefix="/features", tags=["Features"])


@router.get("/")
async def get_all_features(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await crud.get_features(db)


@router.post("/")
async def create_feature(
    feature: FeatureCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin)
):
    return await crud.create_feature(db, feature)


@router.patch("/{feature_id}")
async def update_feature(
    feature_id: int,
    data: FeatureUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin)
):
    return await crud.update_feature(db, feature_id, data)


@router.delete("/{feature_id}")
async def delete_feature(
    feature_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin)
):
    return await crud.delete_feature(db, feature_id)
