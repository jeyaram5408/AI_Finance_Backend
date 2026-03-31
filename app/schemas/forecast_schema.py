from pydantic import BaseModel

class ForecastResponse(BaseModel):
    monthly_avg: float
    next_month: float
    six_month: float