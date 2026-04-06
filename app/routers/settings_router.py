from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.dependencies.auth_dependency import get_current_user
from app.dependencies.db import get_db
from app.models.settings_model import UserSettingsClass
from app.models.user_table_model import UserTableClass
from app.schemas.settings_schema import SettingsUpdate

router = APIRouter(prefix="/settings", tags=["Settings"])


async def get_or_create_settings(db: AsyncSession, current_user: UserTableClass):
    result = await db.execute(
        select(UserSettingsClass).where(UserSettingsClass.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        now = datetime.utcnow()
        settings = UserSettingsClass(
            user_id=current_user.id,
            currency="INR",
            monthly_budget=None,
            email_notifications=True,
            push_notifications=False,
            budget_alerts=True,
            created_at=now,
            updated_at=now
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


def build_settings_response(user: UserTableClass, settings: UserSettingsClass):
    return {
        "name": user.name,
        "email": user.email,
        "phone_number": user.phone_number,
        "currency": settings.currency,
        "monthly_budget": settings.monthly_budget,
        "email_notifications": settings.email_notifications,
        "push_notifications": settings.push_notifications,
        "budget_alerts": settings.budget_alerts,
    }


@router.get("/me")
async def get_my_settings(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    settings = await get_or_create_settings(db, current_user)

    return {
        "success": True,
        "message": "Settings fetched successfully",
        "data": build_settings_response(current_user, settings)
    }


@router.patch("/me")
async def update_my_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    update_data = data.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    settings = await get_or_create_settings(db, current_user)
    now = datetime.utcnow()

    try:
        # ---------------- PROFILE / ACCOUNT ----------------
        if "name" in update_data and update_data["name"] is not None:
            current_user.name = " ".join(update_data["name"].split())

        if "email" in update_data and update_data["email"] is not None:
            new_email = update_data["email"].lower().strip()

            if new_email != current_user.email.lower():
                email_check = await db.execute(
                    select(UserTableClass).where(
                        UserTableClass.email == new_email,
                        UserTableClass.id != current_user.id
                    )
                )
                existing_email = email_check.scalar_one_or_none()

                if existing_email:
                    raise HTTPException(status_code=400, detail="Email already in use")

                current_user.email = new_email

        if "phone_number" in update_data and update_data["phone_number"] is not None:
            new_phone = update_data["phone_number"].strip()

            if new_phone != (current_user.phone_number or ""):
                phone_check = await db.execute(
                    select(UserTableClass).where(
                        UserTableClass.phone_number == new_phone,
                        UserTableClass.id != current_user.id
                    )
                )
                existing_phone = phone_check.scalar_one_or_none()

                if existing_phone:
                    raise HTTPException(status_code=400, detail="Phone number already exists")

                current_user.phone_number = new_phone

        if "password" in update_data and update_data["password"]:
            current_user.password = hash_password(update_data["password"])

        # ---------------- SETTINGS TABLE ----------------
        if "currency" in update_data and update_data["currency"] is not None:
            settings.currency = update_data["currency"]

        if "monthly_budget" in update_data:
            settings.monthly_budget = update_data["monthly_budget"]

        if "email_notifications" in update_data:
            settings.email_notifications = update_data["email_notifications"]

        if "push_notifications" in update_data:
            settings.push_notifications = update_data["push_notifications"]

        if "budget_alerts" in update_data:
            settings.budget_alerts = update_data["budget_alerts"]

        current_user.updated_at = now
        settings.updated_at = now

        await db.commit()
        await db.refresh(current_user)
        await db.refresh(settings)

        return {
            "success": True,
            "message": "Settings updated successfully",
            "data": build_settings_response(current_user, settings)
        }

    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        print("🔥 Settings Update Error:", e)
        raise HTTPException(status_code=500, detail="Failed to update settings")
