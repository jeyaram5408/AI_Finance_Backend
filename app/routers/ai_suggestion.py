from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_table_model import UserTableClass
from app.services.ai_suggestion_service import generate_ai_suggestions

router = APIRouter(prefix="/suggestions", tags=["AI Suggestions"])


@router.get("/")
async def get_ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    return await generate_ai_suggestions(db, current_user.id)
