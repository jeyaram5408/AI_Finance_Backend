from app.core.security import hash_password
from app.models.user_table_model import PersonalDetailsClass, UserTableClass
from app.routers.user_api import IST
from app.models.user_table_model import UserTableClass
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user_schemas import UserRead, UserUpdate

from datetime import datetime

from app.services import user
async def update_user(db: AsyncSession, user: UserTableClass, data):
    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("role", None)
    # ---------------- USER TABLE UPDATE ----------------
    for key, value in update_data.items():
        if value is None:
           continue   # 🔥 skip null values
        if key == "password" and value:
            setattr(user, key, hash_password(value))
        elif key != "personal":
            setattr(user, key, value)

    # ---------------- PERSONAL TABLE UPDATE ----------------
    if "personal" in update_data:
        personal_data = update_data["personal"]

        if user.personal:
            # update existing
            for key, value in personal_data.items():

                if value is None:
                   continue   # 🔥 skip null values
                if key == "address" and isinstance(value, dict):
                    current_address = user.personal.address or {}
                    current_address.update(value)
                    user.personal.address = current_address
                else:
                    setattr(user.personal, key, value)
        else:
            # create new personal record
            new_personal = PersonalDetailsClass(
                usertable_id=user.id,
                **personal_data
            )
            db.add(new_personal)

    # ---------------- TIMESTAMP ----------------
    user.updated_at = datetime.now(IST)

    await db.commit()
    await db.refresh(user)

    return user