from datetime import datetime
import pytz

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.dependencies.auth_dependency import require_admin
from app.dependencies.db import get_db
from app.models.user_table_model import UserTableClass, PersonalDetailsClass
from app.schemas.pagination import PaginatedResponse
from app.schemas.response import APIResponse
from app.schemas.user_schemas import UserCreate, UserRead, UserUpdate
from app.utils.pagination_utils import paginate_query


router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(require_admin)]
)

IST = pytz.timezone("Asia/Kolkata")
EXCLUDED_ROLES = {"superadmin", "admin"}


def now_ist():
    return datetime.now(IST)


@router.post("/create", response_model=APIResponse[UserRead])
async def create_users(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        role = (data.role or "user").lower()

        if role in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="You are not allowed to create SuperAdmin or Admin users")

        result = await db.execute(select(UserTableClass).where(UserTableClass.email == data.email.lower()))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

        if data.phone_number:
            phone_check = await db.execute(select(UserTableClass).where(UserTableClass.phone_number == data.phone_number))
            if phone_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Phone number already exists")

        now = now_ist()

        new_user = UserTableClass(
            role=role,
            user_id=data.user_id,
            name=data.name,
            email=data.email.lower(),
            phone_number=data.phone_number,
            password=hash_password(data.password),
            monthly_income=data.monthly_income,
            occupation=data.occupation,
            savings_goal=data.savings_goal,
            is_active=True,
            is_verified=True,
            provider="local",
            created_at=now,
            updated_at=now,
        )

        db.add(new_user)
        await db.flush()

        if not new_user.user_id:
            new_user.user_id = f"AFA{new_user.id:02d}"

        if data.personal:
            personal_details = PersonalDetailsClass(
                usertable_id=new_user.id,
                gender=data.personal.gender,
                date_of_birth=data.personal.date_of_birth,
                address=data.personal.address.model_dump(exclude_none=True) if data.personal.address else None,
                nationality=data.personal.nationality,
                favnum=data.personal.favnum,
                emergencynumber=data.personal.emergencynumber,
                created_at=now,
                updated_at=now,
            )
            db.add(personal_details)

        await db.commit()

        result = await db.execute(
            select(UserTableClass)
            .options(selectinload(UserTableClass.personal))
            .where(UserTableClass.id == new_user.id)
        )
        new_user = result.scalar_one()

        return {
            "success": True,
            "message": "User created successfully",
            "data": new_user
        }

    except Exception:
        await db.rollback()
        raise


@router.get("/view", response_model=PaginatedResponse[UserRead])
async def view_all_users_with_roles(
    role: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    if role and role.lower() in EXCLUDED_ROLES:
        raise HTTPException(status_code=403, detail="Filtering by this role is not allowed.")

    base_query = (
        select(UserTableClass)
        .where(~func.lower(func.coalesce(UserTableClass.role, "user")).in_(EXCLUDED_ROLES))
        .options(selectinload(UserTableClass.personal))
    )

    if role:
        base_query = base_query.where(func.lower(UserTableClass.role) == role.lower())

    pagination = await paginate_query(db, base_query, page, page_size)
    users = pagination["result"].scalars().all()

    return PaginatedResponse(
        items=users,
        total_records=pagination["total"],
        page_no=page,
        page_size=page_size,
        total_pages=pagination["total_pages"]
    )


@router.patch("/update/{id}", response_model=APIResponse[UserRead])
async def update_users_details(
    id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    now = now_ist()

    try:
        update_data = data.model_dump(exclude_unset=True)

        if "role" in update_data:
            raise HTTPException(status_code=403, detail="Role changes are not allowed via this endpoint")

        stmt = await db.execute(
            select(UserTableClass)
            .where(UserTableClass.id == id)
            .options(selectinload(UserTableClass.personal))
        )
        target_user = stmt.scalar_one_or_none()

        if not target_user:
            raise HTTPException(status_code=404, detail="Target User not found")

        if (target_user.role or "").lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="SuperAdmin and Admin users cannot be modified")

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        if data.user_id and data.user_id != target_user.user_id:
            user_id_check = await db.execute(
                select(UserTableClass).where(
                    UserTableClass.user_id == data.user_id,
                    UserTableClass.id != target_user.id
                )
            )
            if user_id_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="User ID already exists")

        if data.phone_number and data.phone_number != target_user.phone_number:
            phone_check = await db.execute(
                select(UserTableClass).where(
                    UserTableClass.phone_number == data.phone_number,
                    UserTableClass.id != target_user.id
                )
            )
            if phone_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Phone number already exists")

        if data.email and data.email.lower() != target_user.email.lower():
            email_check = await db.execute(
                select(UserTableClass).where(
                    UserTableClass.email == data.email.lower(),
                    UserTableClass.id != target_user.id
                )
            )
            if email_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already in use")
            target_user.email = data.email.lower()

        user_fields = [
            "user_id", "name", "phone_number", "is_active",
            "monthly_income", "occupation", "savings_goal"
        ]

        for field in user_fields:
            if field in update_data:
                setattr(target_user, field, update_data[field])

        if data.password:
            target_user.password = hash_password(data.password)

        target_user.updated_at = now

        if data.personal:
            personal_data = data.personal.model_dump(exclude_unset=True)

            if target_user.personal:
                for field, value in personal_data.items():
                    if field == "address" and value:
                        current_address = target_user.personal.address or {}
                        current_address.update(value)
                        target_user.personal.address = current_address
                    else:
                        setattr(target_user.personal, field, value)

                target_user.personal.updated_at = now
            else:
                new_personal = PersonalDetailsClass(
                    usertable_id=target_user.id,
                    **personal_data,
                    created_at=now,
                    updated_at=now
                )
                db.add(new_personal)

        await db.commit()
        await db.refresh(target_user)

        result = await db.execute(
            select(UserTableClass)
            .options(selectinload(UserTableClass.personal))
            .where(UserTableClass.id == target_user.id)
        )
        target_user = result.scalar_one()

        return {
            "success": True,
            "message": "User updated successfully",
            "data": target_user
        }

    except Exception:
        await db.rollback()
        raise


@router.delete("/hard_delete_user/{id}", response_model=APIResponse[None])
async def hard_delete_user(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        result = await db.execute(select(UserTableClass).where(UserTableClass.id == id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if (user.role or "").lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="SuperAdmin and Admin users cannot be deleted")

        await db.delete(user)
        await db.commit()

        return {
            "success": True,
            "message": f"User '{user.name}' deleted permanently",
            "data": None
        }

    except Exception:
        await db.rollback()
        raise
