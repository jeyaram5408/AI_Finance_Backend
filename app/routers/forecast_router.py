from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_table_model import UserTableClass
from app.services.forecast_service import get_monthly_expenses, calculate_forecast

router = APIRouter(prefix="/forecast", tags=["Forecast"])


from app.schemas.forecast_schema import ForecastResponse

@router.get("/", response_model=ForecastResponse)
async def get_forecast(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    monthly_data = await get_monthly_expenses(db, current_user.id)
    forecast = calculate_forecast(monthly_data)
    return forecast