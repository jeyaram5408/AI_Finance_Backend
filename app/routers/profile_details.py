from datetime import datetime
import pytz

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.core.security import hash_password
from app.models.user_table_model import UserTableClass, PersonalDetailsClass
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.db import get_db
from app.schemas.user_schemas import UserUpdate

router = APIRouter(prefix="/profile", tags=["Profile"])

IST = pytz.timezone("Asia/Kolkata")


def build_profile_response(user: UserTableClass):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "user_id": user.user_id,
        "phone_number": user.phone_number,
        "role": user.role,
        "is_active": user.is_active,
        "profile_picture": user.profile_picture,
        "monthly_income": getattr(user, "monthly_income", None),
        "occupation": getattr(user, "occupation", None),
        "savings_goal": getattr(user, "savings_goal", None),
        "personal": {
            "gender": user.personal.gender if user.personal else None,
            "date_of_birth": user.personal.date_of_birth if user.personal else None,
            "address": user.personal.address if user.personal else None,
            "emergencynumber": user.personal.emergencynumber if user.personal else None,
        }
    }


@router.get("/users/me")
async def get_my_profile(current_user: UserTableClass = Depends(get_current_user)):
    return {
        "success": True,
        "message": "Profile fetched successfully",
        "data": build_profile_response(current_user)
    }


@router.patch("/users/me")
async def update_my_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    now = datetime.now(IST)

    try:
        if "email" in update_data and update_data["email"]:
            new_email = update_data["email"].lower().strip()

            if new_email != current_user.email.lower():
                email_check = await db.execute(
                    select(UserTableClass).where(
                        UserTableClass.email == new_email,
                        UserTableClass.id != current_user.id
                    )
                )
                if email_check.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="Email already in use")

                current_user.email = new_email

        if "phone_number" in update_data and update_data["phone_number"]:
            new_phone = update_data["phone_number"].strip()

            if new_phone != (current_user.phone_number or ""):
                phone_check = await db.execute(
                    select(UserTableClass).where(
                        UserTableClass.phone_number == new_phone,
                        UserTableClass.id != current_user.id
                    )
                )
                if phone_check.scalar_one_or_none():
                    raise HTTPException(status_code=400, detail="Phone number already exists")

                current_user.phone_number = new_phone

        if "name" in update_data:
            current_user.name = update_data["name"]

        if "monthly_income" in update_data:
            current_user.monthly_income = update_data["monthly_income"]

        if "occupation" in update_data:
            current_user.occupation = update_data["occupation"]

        if "savings_goal" in update_data:
            current_user.savings_goal = update_data["savings_goal"]

        if "password" in update_data:
            if not update_data["password"]:
                raise HTTPException(status_code=400, detail="Password cannot be empty")
            current_user.password = hash_password(update_data["password"])

        if "personal" in update_data and update_data["personal"] is not None:
            personal_data = update_data["personal"]

            if current_user.personal:
                for key, value in personal_data.items():
                    if key == "address" and value:
                        current_address = current_user.personal.address or {}
                        current_address.update(value)
                        current_user.personal.address = current_address
                    else:
                        setattr(current_user.personal, key, value)

                current_user.personal.updated_at = now
            else:
                new_personal = PersonalDetailsClass(
                    usertable_id=current_user.id,
                    gender=personal_data.get("gender"),
                    date_of_birth=personal_data.get("date_of_birth"),
                    address=personal_data.get("address"),
                    emergencynumber=personal_data.get("emergencynumber"),
                    created_at=now,
                    updated_at=now
                )
                db.add(new_personal)

        current_user.updated_at = now

        await db.commit()

        result = await db.execute(
            select(UserTableClass)
            .options(selectinload(UserTableClass.personal))
            .where(UserTableClass.id == current_user.id)
        )
        updated_user = result.scalar_one()

        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": build_profile_response(updated_user)
        }

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print("Profile Update Error:", e)
        raise HTTPException(status_code=500, detail="Failed to update profile")
