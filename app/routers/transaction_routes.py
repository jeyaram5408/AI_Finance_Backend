from fastapi import APIRouter, Depends,Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.user_table_model import UserTableClass
from app.schemas.transaction_schema import TransactionCreate, TransactionUpdate
from app.services import transaction_crud as crud
from app.models.transaction_model import Transaction
router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.post("/")
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    return await crud.create_transaction(db, data, current_user.id)


@router.get("/")
async def get_all_transactions(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    return await crud.get_all_transactions(db, current_user.id)

# ✅ NORMAL (Dashboard)

@router.get("/paginated")
async def get_transactions_paginated(
    page: int = Query(1, ge=1),
    limit: int = Query(5, le=100),
    filter: str = "all",
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    return await crud.get_transactions_paginated(
        db, current_user.id, page, limit, filter
    )

@router.patch("/{txn_id}")
async def update_transaction(
    txn_id: int,
    data: TransactionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    return await crud.update_transaction(db, txn_id, data, current_user.id)


@router.delete("/{txn_id}")
async def delete_transaction(
    txn_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user),
):
    return await crud.delete_transaction(db, txn_id, current_user.id)
