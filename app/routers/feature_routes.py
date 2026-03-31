from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from app.schemas.feature_schema import FeatureCreate, FeatureUpdate
from app.services import feature_crud as crud


router = APIRouter(prefix="/features", tags=["Features"])


@router.post("/")
async def create_feature(feature: FeatureCreate, db: AsyncSession = Depends(get_db)):
    return await crud.create_feature(db, feature)


@router.get("/")
async def get_all_features(db: AsyncSession = Depends(get_db)):
    return await crud.get_features(db)


@router.patch("/{feature_id}")
async def update_feature(feature_id: int, data: FeatureUpdate, db: AsyncSession = Depends(get_db)):
    return await crud.update_feature(db, feature_id, data)


@router.delete("/{feature_id}")
async def delete_feature(feature_id: int, db: AsyncSession = Depends(get_db)):
    return await crud.delete_feature(db, feature_id)