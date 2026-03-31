from sqlalchemy import select
from app.models.feature_model import Feature


async def create_feature(db, feature):
    new_feature = Feature(**feature.dict())

    db.add(new_feature)
    await db.commit()
    await db.refresh(new_feature)

    return new_feature


async def get_features(db):
    result = await db.execute(select(Feature))
    return result.scalars().all()


async def update_feature(db, feature_id: int, data):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()

    if feature:
        for key, value in data.dict(exclude_unset=True).items():
            setattr(feature, key, value)

        await db.commit()
        await db.refresh(feature)

    return feature


async def delete_feature(db, feature_id: int):
    result = await db.execute(select(Feature).where(Feature.id == feature_id))
    feature = result.scalar_one_or_none()

    if feature:
        await db.delete(feature)
        await db.commit()

    return feature