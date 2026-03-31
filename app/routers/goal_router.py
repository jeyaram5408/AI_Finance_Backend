from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_table_model import UserTableClass
from app.schemas.goal_schema import (
    GoalCreateSchema,
    GoalUpdateSchema,
    GoalContributionCreateSchema,
)
from app.services import goal_crud


router = APIRouter(prefix="/goals", tags=["Goals"])


@router.post("/")
async def create_goal(
    data: GoalCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await goal_crud.create_goal(db, current_user.id, data)


@router.get("/")
async def get_all_goals(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await goal_crud.get_goals(db, current_user.id)


@router.put("/{goal_id}")
async def update_goal(
    goal_id: int,
    data: GoalUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await goal_crud.update_goal(db, goal_id, current_user.id, data)


@router.post("/{goal_id}/contribute")
async def add_contribution(
    goal_id: int,
    data: GoalContributionCreateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await goal_crud.add_contribution(db, goal_id, current_user.id, data)


@router.get("/{goal_id}/contributions")
async def get_contributions(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await goal_crud.get_goal_contributions(db, goal_id, current_user.id)


@router.patch("/{goal_id}/complete")
async def complete_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await goal_crud.complete_goal_manually(db, goal_id, current_user.id)


@router.delete("/{goal_id}")
async def delete_goal(
    goal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    return await goal_crud.delete_goal(db, goal_id, current_user.id)
