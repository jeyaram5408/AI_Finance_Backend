from datetime import date
from typing import Optional, Literal
from pydantic import BaseModel, Field


class GoalCreateSchema(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    target_amount: float = Field(..., gt=0)
    duration_days: int = Field(..., gt=0)
    start_date: Optional[date] = None


class GoalUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    target_amount: Optional[float] = Field(None, gt=0)
    duration_days: Optional[int] = Field(None, gt=0)
    start_date: Optional[date] = None
    status: Optional[Literal["in_progress", "completed", "overdue", "cancelled"]] = None


class GoalContributionCreateSchema(BaseModel):
    amount: float = Field(..., gt=0)
    contribution_date: Optional[date] = None
    note: Optional[str] = None
    frequency_type: Optional[Literal["daily", "weekly", "monthly", "manual"]] = "manual"
