from datetime import date, timedelta
from math import ceil
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.savings_goals import SavingsGoal,GoalContribution

from app.schemas.goal_schema import (
    GoalCreateSchema,
    GoalUpdateSchema,
    GoalContributionCreateSchema,
)


def refresh_goal_status(goal: SavingsGoal):
    today = date.today()

    if goal.status == "cancelled":
        return goal.status

    if float(goal.saved_amount or 0) >= float(goal.target_amount or 0):
        goal.status = "completed"
    elif today > goal.end_date:
        goal.status = "overdue"
    else:
        goal.status = "in_progress"

    return goal.status


def serialize_goal(goal: SavingsGoal):
    refresh_goal_status(goal)

    target = float(goal.target_amount or 0)
    saved = float(goal.saved_amount or 0)
    progress = round(min((saved / target) * 100, 100), 1) if target > 0 else 0
    remaining_amount = round(max(target - saved, 0), 2)

    today = date.today()
    remaining_days = max((goal.end_date - today).days, 0)
    remaining_months = ceil(remaining_days / 30) if remaining_days > 0 else 0

    daily_target = round(remaining_amount / remaining_days, 2) if remaining_days > 0 else 0
    monthly_target = round(remaining_amount / remaining_months, 2) if remaining_months > 0 else 0

    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": round(target, 2),
        "saved_amount": round(saved, 2),
        "progress": progress,
        "remaining_amount": remaining_amount,
        "duration_days": goal.duration_days,
        "remaining_days": remaining_days,
        "daily_target": daily_target,
        "monthly_target": monthly_target,
        "status": goal.status,
        "start_date": goal.start_date,
        "end_date": goal.end_date,
        "created_at": goal.created_at,
    }


def serialize_contribution(contribution: GoalContribution):
    return {
        "id": contribution.id,
        "goal_id": contribution.goal_id,
        "user_id": contribution.user_id,
        "amount": round(float(contribution.amount or 0), 2),
        "contribution_date": contribution.contribution_date,
        "note": contribution.note,
        "frequency_type": contribution.frequency_type,
        "created_at": contribution.created_at,
    }


async def get_goal_or_404(db: AsyncSession, goal_id: int, user_id: int) -> SavingsGoal:
    result = await db.execute(
        select(SavingsGoal).where(
            SavingsGoal.id == goal_id,
            SavingsGoal.user_id == user_id
        )
    )
    goal = result.scalar_one_or_none()

    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")

    return goal


async def create_goal(db: AsyncSession, user_id: int, data: GoalCreateSchema):
    start_date = data.start_date or date.today()
    end_date = start_date + timedelta(days=data.duration_days)

    goal = SavingsGoal(
        user_id=user_id,
        name=data.name.strip(),
        target_amount=float(data.target_amount),
        saved_amount=0,
        start_date=start_date,
        end_date=end_date,
        duration_days=data.duration_days,
        status="in_progress",
    )

    db.add(goal)
    await db.commit()
    await db.refresh(goal)

    return {
        "message": "Goal created successfully",
        "data": serialize_goal(goal)
    }


async def get_goals(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(SavingsGoal)
        .where(SavingsGoal.user_id == user_id)
        .order_by(SavingsGoal.created_at.desc())
    )
    goals = result.scalars().all()

    changed = False
    serialized = []

    for goal in goals:
        old_status = goal.status
        refresh_goal_status(goal)
        if old_status != goal.status:
            changed = True
        serialized.append(serialize_goal(goal))

    if changed:
        await db.commit()

    in_progress = [g for g in serialized if g["status"] == "in_progress"]
    completed = [g for g in serialized if g["status"] == "completed"]
    overdue = [g for g in serialized if g["status"] == "overdue"]
    cancelled = [g for g in serialized if g["status"] == "cancelled"]

    nearest_goal = None
    if in_progress:
        nearest_goal = min(in_progress, key=lambda x: x["remaining_days"])

    return {
        "all": serialized,
        "in_progress": in_progress,
        "completed": completed,
        "overdue": overdue,
        "cancelled": cancelled,
        "summary": {
            "active_goals_count": len(in_progress),
            "completed_goals_count": len(completed),
            "total_target_amount": round(sum(g["target_amount"] for g in serialized), 2),
            "total_saved_amount": round(sum(g["saved_amount"] for g in serialized), 2),
            "nearest_goal": nearest_goal,
        }
    }


async def update_goal(db: AsyncSession, goal_id: int, user_id: int, data: GoalUpdateSchema):
    goal = await get_goal_or_404(db, goal_id, user_id)

    if data.name is not None:
        goal.name = data.name.strip()

    if data.target_amount is not None:
        goal.target_amount = float(data.target_amount)

    if data.start_date is not None:
        goal.start_date = data.start_date

    if data.duration_days is not None:
        goal.duration_days = data.duration_days

    if data.start_date is not None or data.duration_days is not None:
        goal.end_date = goal.start_date + timedelta(days=goal.duration_days)

    if data.status is not None:
        goal.status = data.status

    refresh_goal_status(goal)

    await db.commit()
    await db.refresh(goal)

    return {
        "message": "Goal updated successfully",
        "data": serialize_goal(goal)
    }


async def add_contribution(
    db: AsyncSession,
    goal_id: int,
    user_id: int,
    data: GoalContributionCreateSchema
):
    goal = await get_goal_or_404(db, goal_id, user_id)

    if goal.status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot add money to a cancelled goal")

    contribution = GoalContribution(
        goal_id=goal.id,
        user_id=user_id,
        amount=float(data.amount),
        contribution_date=data.contribution_date or date.today(),
        note=data.note,
        frequency_type=data.frequency_type or "manual",
    )

    db.add(contribution)
    goal.saved_amount = round(float(goal.saved_amount or 0) + float(data.amount), 2)

    refresh_goal_status(goal)

    await db.commit()
    await db.refresh(goal)
    await db.refresh(contribution)

    return {
        "message": "Contribution added successfully",
        "data": {
            "goal": serialize_goal(goal),
            "contribution": serialize_contribution(contribution)
        }
    }


async def get_goal_contributions(db: AsyncSession, goal_id: int, user_id: int):
    await get_goal_or_404(db, goal_id, user_id)

    result = await db.execute(
        select(GoalContribution)
        .where(
            GoalContribution.goal_id == goal_id,
            GoalContribution.user_id == user_id
        )
        .order_by(GoalContribution.contribution_date.desc(), GoalContribution.id.desc())
    )
    rows = result.scalars().all()

    return {
        "goal_id": goal_id,
        "contributions": [serialize_contribution(row) for row in rows]
    }


async def delete_goal(db: AsyncSession, goal_id: int, user_id: int):
    goal = await get_goal_or_404(db, goal_id, user_id)

    await db.delete(goal)
    await db.commit()

    return {
        "message": "Goal deleted successfully"
    }


async def complete_goal_manually(db: AsyncSession, goal_id: int, user_id: int):
    goal = await get_goal_or_404(db, goal_id, user_id)
    goal.status = "completed"

    await db.commit()
    await db.refresh(goal)

    return {
        "message": "Goal marked as completed",
        "data": serialize_goal(goal)
    }
