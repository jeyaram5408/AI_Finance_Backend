from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
import pytz
from app.utils.pagination_utils import paginate_query
from app.dependencies.db import get_db
from app.core.security import hash_password

from app.schemas.response import APIResponse
from app.schemas.pagination import PaginatedResponse

from app.models.user_table_model import UserTableClass, PersonalDetailsClass
from app.schemas.user_schemas import UserCreate,UserRead,UserUpdate



# -----------------------------------------------------------------------------------

router = APIRouter(prefix="/users", tags=["Users"])


IST = pytz.timezone("Asia/Kolkata")
def today_ist():
    return datetime.now(IST).date()


EXCLUDED_ROLES = {"superadmin", "admin"}



# ======================================== CREATE ===========================================

# --------- Create Users API ----------

@router.post("/create", response_model=APIResponse[UserRead])
async def create_users(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    now = datetime.combine(today_ist(), datetime.now(IST).time())

    try:

        # ------------------- Check if new user's email already exists --------------------
        result = await db.execute(select(UserTableClass).where(UserTableClass.email == data.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise HTTPException(status_code=400, detail=("Email already registered"))

        # ------------------- Excluding Admins --------------------
        if data.role.lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="You are not allowed to create SuperAdmin or Admin users")

        # ------------------- Hash the password --------------------
        hashed_password = hash_password(data.password)

        # ------------------- Create User --------------------
        new_user = UserTableClass(
            user_id=data.user_id,
            role=data.role,
            name=data.name,
            email=data.email.lower(),
            phone_number=data.phone_number,
            password=hashed_password,
            created_at=now
        )
        db.add(new_user)
        await db.flush()

        # ------------------- Create personal details --------------------
        if data.personal:
            personal_details = PersonalDetailsClass(
                usertable_id=new_user.id,
                gender=data.personal.gender,
                date_of_birth=data.personal.date_of_birth,
                address=data.personal.address.model_dump(exclude_none=True) if data.personal.address else None,
                nationality=data.personal.nationality,
                favnum=data.personal.favnum,
                emergencynumber=data.personal.emergencynumber,
                created_at=now
            )
            db.add(personal_details)

        # ------------------- Commit --------------------
        await db.commit()
        await db.refresh(new_user)

        # ------------------- Reload user with personal (Eager Loading) --------------------
        result = await db.execute(
            select(UserTableClass)
            .options(selectinload(UserTableClass.personal))
            .where(UserTableClass.id == new_user.id)
        )
        new_user = result.scalar_one()

        # ------------------- Return response --------------------
        return {
            "success": True,
            "message": "User created successfully",
            "data": new_user
        }

    # ------------------- Errors --------------------
    except Exception:
        await db.rollback()
        raise







# ======================================== VIEW ===========================================

# --------- View All Users with Roles API ----------

@router.get("/view", response_model=PaginatedResponse[UserRead])
async def view_all_users_with_roles(
    role: str | None = None,
    page: int = Query(default=1, ge=1, description="Page number (starts from 1)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Number of users per page"),
    db: AsyncSession = Depends(get_db)
):
    # ------------------- Block restricted roles from query param --------------------
    if role and role.lower() in EXCLUDED_ROLES:
        raise HTTPException(status_code=403, detail="Filtering by this role is not allowed.")

    # ------------------- Build Base Query --------------------
    base_query = (
        select(UserTableClass)
        .where(~func.lower(UserTableClass.role).in_(EXCLUDED_ROLES))
        .options(selectinload(UserTableClass.personal))
    )

    # ------------------- Optional Role Filter --------------------
    if role:
        base_query = base_query.where(func.lower(UserTableClass.role) == role.lower())

    # -------- Call Pagination Utility --------
    pagination = await paginate_query(db, base_query, page, page_size)

    users = pagination["result"].scalars().all()

    # ------------------- Return Paginated Response --------------------
    return PaginatedResponse(
        items=users,
        total_records=pagination["total"],
        page_no=page,
        page_size=page_size,
        total_pages=pagination["total_pages"]
    )


# ======================================== UPDATE ===========================================

# --------- Update Users Details API ----------

@router.patch("/update/{id}", response_model=APIResponse[UserRead])
async def update_users_details(
    id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.combine(today_ist(), datetime.now(IST).time())

    try:
        update_data = data.model_dump(exclude_unset=True)  # move this UP first
        if "role" in update_data:
            raise HTTPException(
                 status_code=403,
                 detail="Role changes are not allowed via this endpoint"
    )

        # ------------------- Fetch Target User --------------------
        stmt = await db.execute(
            select(UserTableClass)
            .where(UserTableClass.id == id)
            .options(selectinload(UserTableClass.personal))
        )
        target_user = stmt.scalar_one_or_none()

        if not target_user:
            raise HTTPException(status_code=404, detail="Target User not found")

        # ------------------- Restrict Admin / SuperAdmin --------------------
        if target_user.role and target_user.role.lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="SuperAdmin and Admin users cannot be modified")

        if data.role and data.role.lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="You cannot assign SuperAdmin or Admin role")

        # ------------------- Get update data --------------------
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        # ------------------- Check user_id uniqueness -------------------
        if data.user_id and data.user_id != target_user.user_id:
            user_id_check = await db.execute(select(UserTableClass).where(UserTableClass.user_id == data.user_id))

            if user_id_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="User ID already exists")

        # ------------------- Check phone number uniqueness -------------------
        if data.phone_number and data.phone_number != target_user.phone_number:
            phone_check = await db.execute(select(UserTableClass).where(UserTableClass.phone_number == data.phone_number))

            if phone_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Phone number already exists")

        # ------------------- Update Users Table Fields -------------------
        user_fields = ["user_id", "name", "phone_number", "is_active", "monthly_income", "occupation", "savings_goal"]

        for field in user_fields:
            if field in update_data:
                setattr(target_user, field, update_data[field])

        # ------------------- Check Email Availability --------------------
        if data.email and data.email.lower() != target_user.email.lower():
            email_check = await db.execute(select(UserTableClass).where(UserTableClass.email == data.email.lower()))

            if email_check.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Email already in use")

            else:
                target_user.email = data.email.lower()

        # ------------------- Update Password --------------------
        if data.password:
            target_user.password = hash_password(data.password)

        target_user.updated_at = now

        # ------------------- Update or Create PersonalDetails --------------------
        if data.personal:
            personal_data = data.personal.model_dump(exclude_unset=True)

            if target_user.personal:
                # Update existing record
                for field, value in personal_data.items():
                    if field == "address" and value:
                        current_address = target_user.personal.address or {}
                        current_address.update(value)
                        target_user.personal.address = current_address
                    else:
                        setattr(target_user.personal, field, value)
                target_user.personal.updated_at = now

            else:
                # Create new personal record
                new_personal = PersonalDetailsClass(
                    usertable_id=target_user.id,
                    **personal_data,
                    created_at=now
                )
                db.add(new_personal)

        # ------------------- Commit --------------------
        await db.commit()
        await db.refresh(target_user, attribute_names=["personal"])

      

        # ------------------- Return response --------------------
        return {
            "success": True,
            "message": "User Updated successfully",
            "data": target_user
        }

    # ------------------- Errors --------------------
    except Exception:
        await db.rollback()
        raise




# ======================================== DELETE ===========================================

# --------- Hard Delete User API ----------

@router.delete("/hard_delete_user/{id}", response_model=APIResponse[None])
async def hard_delete_user(
    id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        # ------------------- Fetch User --------------------
        result = await db.execute(select(UserTableClass).where(UserTableClass.id == id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # ------------------- Excluding Admins --------------------
        if user.role and user.role.lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="SuperAdmin and Admin users cannot be deleted")

        # ------------------- Hard Delete --------------------
        await db.delete(user)

        # ------------------- Commit --------------------
        await db.commit()

        # ------------------- Return response --------------------
        return {
            "success": True,
            "message": f"User '{user.name}' deleted permanently",
            "data": None
        }

    # ------------------- Errors --------------------
    except Exception:
        await db.rollback()
        raise   
    
    # --------- Full Update User API (PUT) ----------
@router.put("/full_update/{id}", response_model=APIResponse[UserRead])
async def full_update_user(
    id: int,
    data: UserUpdate,  # Use full UserCreate schema
    db: AsyncSession = Depends(get_db)
):
    now = datetime.combine(today_ist(), datetime.now(IST).time())

    try:
        # ------------------- Fetch Target User --------------------
        stmt = await db.execute(
            select(UserTableClass)
            .where(UserTableClass.id == id)
            .options(selectinload(UserTableClass.personal))
        )
        target_user = stmt.scalar_one_or_none()

        if not target_user:
            raise HTTPException(status_code=404, detail="User not found")

        # ------------------- Restrict Admin / SuperAdmin --------------------
        if target_user.role and target_user.role.lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="SuperAdmin and Admin users cannot be modified")

        if data.role.lower() in EXCLUDED_ROLES:
            raise HTTPException(status_code=403, detail="You cannot assign SuperAdmin or Admin role")

        # ------------------- Check Email, Phone, UserID uniqueness --------------------
        email_check = await db.execute(select(UserTableClass).where(UserTableClass.email == data.email.lower(), UserTableClass.id != id))
        if email_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already in use")

        phone_check = await db.execute(select(UserTableClass).where(UserTableClass.phone_number == data.phone_number, UserTableClass.id != id))
        if phone_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Phone number already exists")

        user_id_check = await db.execute(select(UserTableClass).where(UserTableClass.user_id == data.user_id, UserTableClass.id != id))
        if user_id_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User ID already exists")

        # ------------------- Update Users Table Fields --------------------
        target_user.user_id = data.user_id
        # target_user.role = data.role
        target_user.name = data.name
        target_user.email = data.email.lower()
        target_user.phone_number = data.phone_number
        target_user.password = hash_password(data.password)
        target_user.updated_at = now

        # ------------------- Update or Create PersonalDetails --------------------
        personal_data = data.personal.model_dump(exclude_none=True) if data.personal else None
        if personal_data:
            if target_user.personal:
                # Replace existing personal details fully
                for field, value in personal_data.items():
                    if field == "address":
                        target_user.personal.address = value
                    else:
                        setattr(target_user.personal, field, value)
                target_user.personal.updated_at = now
            else:
                # Create new personal details
                new_personal = PersonalDetailsClass(
                    usertable_id=target_user.id,
                    **personal_data,
                    created_at=now
                )
                db.add(new_personal)

        # ------------------- Commit --------------------
        await db.commit()
        await db.refresh(target_user, attribute_names=["personal"])

        # ------------------- Return response --------------------
        return {
            "success": True,
            "message": "User fully updated successfully",
            "data": target_user
        }

    except Exception:
        await db.rollback()
        raise