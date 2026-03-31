from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_table_model import UserTableClass
from app.services.dashboard_service import get_dashboard_data

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
async def dashboard_data(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await get_dashboard_data(db, current_user.id)
