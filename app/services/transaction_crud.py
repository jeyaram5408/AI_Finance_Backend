from fastapi import HTTPException
from sqlalchemy import select
from app.models.transaction_model import Transaction
from sqlalchemy import select, func
from datetime import datetime, timedelta

async def create_transaction(db, data, user_id: int):
    new_txn = Transaction(
        type=data.type.lower(),
        title=data.title,
        category=data.category,
        amount=float(data.amount),
        date=data.date,
        user_id=user_id,
    )

    db.add(new_txn)
    await db.commit()
    await db.refresh(new_txn)
    return new_txn


# ✅ NORMAL (Dashboard)
async def get_all_transactions(db, user_id: int):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user_id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    return result.scalars().all()


async def get_transactions_paginated(db, user_id, page, limit, filter):
    query = select(Transaction).where(Transaction.user_id == user_id)

    # ✅ FILTER LOGIC
    if filter == "7d":
        past = datetime.utcnow() - timedelta(days=7)
        query = query.where(Transaction.date >= past)

    elif filter == "1m":
        past = datetime.utcnow() - timedelta(days=30)
        query = query.where(Transaction.date >= past)

    elif filter == "3m":
        past = datetime.utcnow() - timedelta(days=90)
        query = query.where(Transaction.date >= past)

    elif filter == "6m":
        past = datetime.utcnow() - timedelta(days=180)
        query = query.where(Transaction.date >= past)

    elif filter == "1y":
        past = datetime.utcnow() - timedelta(days=365)
        query = query.where(Transaction.date >= past)

    # ✅ TOTAL COUNT
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # ✅ PAGINATION
    offset = (page - 1) * limit

    result = await db.execute(
        query.order_by(Transaction.date.desc())
        .offset(offset)
        .limit(limit)
    )

    transactions = result.scalars().all()

    return {
        "data": transactions,
        "total": total,
        "page": page,
        "limit": limit,
    }
async def update_transaction(db, txn_id: int, data, user_id: int):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == txn_id,
            Transaction.user_id == user_id
        )
    )
    txn = result.scalar_one_or_none()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(txn, key, value)

    await db.commit()
    await db.refresh(txn)
    return txn


async def delete_transaction(db, txn_id: int, user_id: int):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == txn_id,
            Transaction.user_id == user_id
        )
    )
    txn = result.scalar_one_or_none()

    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await db.delete(txn)
    await db.commit()
    return {"success": True, "message": "Transaction deleted successfully"}
