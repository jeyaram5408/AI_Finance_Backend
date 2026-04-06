from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth_dependency import require_admin
from app.dependencies.db import get_db
from app.models.user_table_model import UserTableClass


router = APIRouter(prefix="/admin", tags=["Admin"])

ALLOWED_ROLES = {"user", "moderator", "editor"}
EXCLUDED_ROLES = {"admin", "superadmin", "root"}


@router.patch("/update-role/{id}")
async def update_role(
    id: int,
    role: str,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin)
):
    user = await db.get(UserTableClass, id)

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = role.lower().strip()

    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    if user.role and user.role.lower() in EXCLUDED_ROLES:
        raise HTTPException(status_code=403, detail="Cannot modify system/admin users")

    if role in EXCLUDED_ROLES:
        raise HTTPException(status_code=403, detail="Cannot assign admin/system roles")

    if role not in ALLOWED_ROLES:
        raise HTTPException(status_code=400, detail=f"Allowed roles: {list(ALLOWED_ROLES)}")

    if user.role == role:
        return {
            "success": True,
            "message": "Role already set",
            "user_id": user.id,
            "role": user.role
        }

    user.role = role
    await db.commit()
    await db.refresh(user)

    return {
        "success": True,
        "message": "Role updated successfully",
        "updated_by": current_admin.email,
        "user_id": user.id,
        "new_role": user.role
    }
