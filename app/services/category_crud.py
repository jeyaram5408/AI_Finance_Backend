from sqlalchemy import select
from app.models.category_model import Category


async def create_category(db, data, user):
    new_cat = Category(
        name=data.name,
        type=data.type,
        user_id=user.id,
        user_code=user.user_id
    )

    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)

    return new_cat

async def get_categories(db, user_id):
    result = await db.execute(
        select(Category).where(Category.user_id == user_id)
    )
    return result.scalars().all()


async def delete_category(db, cat_id: int, user_id: int):
    result = await db.execute(
        select(Category).where(
            Category.id == cat_id,
            Category.user_id == user_id
        )
    )
    cat = result.scalar_one_or_none()

    if not cat:
        return {"error": "Category not found or unauthorized"}

    await db.delete(cat)
    await db.commit()

    return {"message": "Deleted successfully"}


async def update_category(db, cat_id: int, data, user_id: int):
    result = await db.execute(
        select(Category).where(
            Category.id == cat_id,
            Category.user_id == user_id
        )
    )
    cat = result.scalar_one_or_none()

    if not cat:
        return {"error": "Category not found or unauthorized"}

    if data.name is not None:
        cat.name = data.name

    if data.type is not None:
        cat.type = data.type

    await db.commit()
    await db.refresh(cat)

    return cat