from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_table_model import UserTableClass
from app.services.report_service import get_report_data

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/")
async def get_reports(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    category: str | None = Query(None),
    type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    return await get_report_data(
        db,
        current_user.id,
        start_date,
        end_date,
        category,
        type,
    )
