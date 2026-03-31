from fastapi import APIRouter, Depends
from app.dependencies.auth_dependency import get_current_user
from app.models.user_table_model import UserTableClass

router = APIRouter(prefix="/info", tags=["INFO"])


@router.get("/")
async def get_info(
    current_user: UserTableClass = Depends(get_current_user)
):
    return {
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "user_id": current_user.user_id
    }