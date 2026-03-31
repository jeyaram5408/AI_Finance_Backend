from sqlalchemy import select
from app.models.category_model import Category


async def create_category(db, data):
    new_cat = Category(**data.dict())

    db.add(new_cat)
    await db.commit()
    await db.refresh(new_cat)

    return new_cat


async def get_categories(db):
    result = await db.execute(select(Category))
    return result.scalars().all()


async def delete_category(db, cat_id: int):
    result = await db.execute(
        select(Category).where(Category.id == cat_id)
    )
    cat = result.scalar_one_or_none()

    if cat:
        await db.delete(cat)
        await db.commit()

    return cat

async def update_category(db, cat_id: int, data):
    result = await db.execute(
        select(Category).where(Category.id == cat_id)
    )
    cat = result.scalar_one_or_none()

    if not cat:
        return {"error": "Category not found"}

    # update fields
    if data.name is not None:
     cat.name = data.name

    if data.type is not None:
     cat.type = data.type  # optional but safe

    await db.commit()
    await db.refresh(cat)

    return cat