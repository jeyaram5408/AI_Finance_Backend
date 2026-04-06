from datetime import datetime
from collections import defaultdict
from passlib.context import CryptContext

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies.db import get_db
from app.dependencies.auth_dependency import require_admin
from app.models.user_table_model import UserTableClass
from app.models.transaction_model import Transaction
from app.models.category_model import Category
from app.models.admin_log_model import AdminLog
from app.schemas.admin_schema import AdminUserRoleUpdate

router = APIRouter(prefix="/admin", tags=["Admin"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# ─────────────────────── Pydantic Models ───────────────────────

class UserStatusUpdate(BaseModel):
    is_active: bool


class CategoryPayload(BaseModel):
    name: str
    type: str


class CategoryUpdatePayload(BaseModel):
    name: str | None = None
    type: str | None = None


class AdminCreatePayload(BaseModel):
    name: str
    email: str
    password: str    


# ─────────────────────── Helper: Add Log ───────────────────────

async def add_admin_log(
    db: AsyncSession,
    admin: UserTableClass,
    action: str,
    target_type: str | None = None,
    target_id: int | None = None,
    description: str | None = None,
):
    log = AdminLog(
        admin_id = admin.id    ,   
        admin_code=admin.admin_code,
        action=action,
        target_type=target_type,
        target_id=target_id,
        description=description,
    )
    db.add(log)
    await db.commit()


# ═══════════════════════ STATS ═══════════════════════

@router.get("/stats")
async def get_admin_stats(
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    total_users = await db.scalar(
        select(func.count()).select_from(UserTableClass)
        .where(func.lower(func.coalesce(UserTableClass.role, "user")) != "admin")
    ) or 0

    active_users = await db.scalar(
        select(func.count()).select_from(UserTableClass)
        .where(
            func.lower(func.coalesce(UserTableClass.role, "user")) != "admin",
            UserTableClass.is_active == True
        )
    ) or 0

    total_transactions = await db.scalar(
        select(func.count()).select_from(Transaction)
    ) or 0

    total_income = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(func.lower(Transaction.type) == "income")
    ) or 0

    total_expense = await db.scalar(
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(func.lower(Transaction.type) == "expense")
    ) or 0

    await add_admin_log(db, current_admin, "VIEW_STATS", "dashboard", description="Viewed admin dashboard stats")

    return {
        "total_users": int(total_users),
        "active_users": int(active_users),
        "blocked_users": int(total_users - active_users),
        "total_transactions": int(total_transactions),
        "total_income": float(total_income),
        "total_expense": float(total_expense),
    }


# ═══════════════════════ USERS ═══════════════════════


@router.post("/create-admin")
async def create_admin(
    payload: AdminCreatePayload,
    secret_key: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    if secret_key != "my_super_secret_123":
        raise HTTPException(status_code=403, detail="Unauthorized")

    result = await db.execute(
        select(UserTableClass).where(UserTableClass.email == payload.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    hashed_password = pwd_context.hash(payload.password)

    new_admin = UserTableClass(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        password=hashed_password,
        role="admin",
        is_active=True,
        is_verified=True,
    )

    db.add(new_admin)
  
    await db.flush()

# user_id (already)
    new_admin.user_id = f"AFA{new_admin.id:02d}"

# ✅ admin_code
    new_admin.admin_code = f"ADM{new_admin.id:02d}"
    await db.commit()
    await db.refresh(new_admin)

    return {
        "success": True,
        "admin_id": new_admin.id,
        "message": "Admin created successfully",
    }

@router.get("/users")
async def get_admin_users(
    search: str | None = Query(None),
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    tx_subquery = (
        select(Transaction.user_id.label("user_id"), func.count(Transaction.id).label("total_transactions"))
        .group_by(Transaction.user_id).subquery()
    )

    stmt = (
        select(UserTableClass, func.coalesce(tx_subquery.c.total_transactions, 0).label("total_transactions"))
        .outerjoin(tx_subquery, tx_subquery.c.user_id == UserTableClass.id)
        .where(func.lower(func.coalesce(UserTableClass.role, "user")) != "admin")
        .order_by(desc(UserTableClass.id))
    )

    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(UserTableClass.name).like(like),
                func.lower(UserTableClass.email).like(like),
                func.lower(func.coalesce(UserTableClass.user_id, "")).like(like),
            )
        )

    if status == "active":
        stmt = stmt.where(UserTableClass.is_active == True)
    elif status == "blocked":
        stmt = stmt.where(UserTableClass.is_active == False)

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
    rows = result.all()

    items = []
    for user, total_txn in rows:
        items.append({
            "id": user.id,
            "user_id": user.user_id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "is_active": user.is_active,
            "is_verified": user.is_verified,
            "created_at": user.created_at,
            "total_transactions": int(total_txn or 0),
        })

    return {
        "items": items,
        "total_records": total,
        "page_no": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.get("/users/{user_id}")
async def get_admin_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    result = await db.execute(
        select(UserTableClass)
        .options(selectinload(UserTableClass.personal))
        .where(UserTableClass.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    tx_result = await db.execute(select(Transaction).where(Transaction.user_id == user.id))
    transactions = tx_result.scalars().all()

    total_income = sum(float(t.amount or 0) for t in transactions if (t.type or "").lower() == "income")
    total_expense = sum(float(t.amount or 0) for t in transactions if (t.type or "").lower() == "expense")

    return {
        "id": user.id,
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "phone_number": user.phone_number,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "created_at": user.created_at,
        "monthly_income": user.monthly_income,
        "occupation": user.occupation,
        "savings_goal": user.savings_goal,
        "personal": {
            "gender": user.personal.gender if user.personal else None,
            "date_of_birth": user.personal.date_of_birth if user.personal else None,
            "address": user.personal.address if user.personal else None,
            "emergencynumber": user.personal.emergencynumber if user.personal else None,
        },
        "stats": {
            "total_transactions": len(transactions),
            "total_income": total_income,
            "total_expense": total_expense,
            "savings": total_income - total_expense,
        }
    }


@router.patch("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    user = await db.get(UserTableClass, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate yourself")
    if user.role and user.role.lower() == "admin":
        raise HTTPException(status_code=403, detail="Cannot change another admin status")

    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)

    await add_admin_log(db, current_admin, "UPDATE_USER_STATUS", "user", user.id,
                        f"Set user active status to {payload.is_active}")

    return {"success": True, "message": "User status updated", "user_id": user.id, "is_active": user.is_active}

@router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    payload: AdminUserRoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    user = await db.get(UserTableClass, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    new_role = payload.role.lower()

    if new_role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")

    old_role = user.role
    user.role = new_role

    await db.commit()
    await db.refresh(user)

    await add_admin_log(
        db,
        current_admin,
        "UPDATE_USER_ROLE",
        "user",
        user.id,
        f"Changed role from {old_role} to {new_role}",
    )

    return {
        "success": True,
        "message": f"User role updated to {new_role}",
    }

@router.get("/admins")
async def get_admins(
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    result = await db.execute(
        select(UserTableClass).where(func.lower(UserTableClass.role) == "admin")
    )
    admins = result.scalars().all()

    return admins

@router.delete("/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    user = await db.get(UserTableClass, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role and user.role.lower() == "admin":
        raise HTTPException(status_code=403, detail="Admin cannot be deleted")

    name = user.name
    await db.delete(user)
    await db.commit()

    await add_admin_log(db, current_admin, "DELETE_USER", "user", user_id, f"Deleted user {name}")

    return {"success": True, "message": f"User '{name}' deleted successfully"}


# ═══════════════════════ TRANSACTIONS ═══════════════════════

@router.get("/transactions")
async def get_admin_transactions(
    search: str | None = Query(None),
    type: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    stmt = (
        select(Transaction, UserTableClass)
        .join(UserTableClass, UserTableClass.id == Transaction.user_id)
        .order_by(desc(Transaction.id))
    )

    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Transaction.title).like(like),
                func.lower(UserTableClass.name).like(like),
                func.lower(UserTableClass.email).like(like),
            )
        )

    if type:
        stmt = stmt.where(func.lower(Transaction.type) == type.lower())
    if category:
        stmt = stmt.where(func.lower(Transaction.category) == category.lower())

    total = await db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    result = await db.execute(stmt.limit(page_size).offset((page - 1) * page_size))
    rows = result.all()

    items = []
    for txn, user in rows:
        items.append({
            "id": txn.id,
            "title": txn.title,
            "amount": float(txn.amount or 0),
            "type": txn.type,
            "category": txn.category,
            "date": txn.date,
            "user_id": user.id,
            "user_name": user.name,
            "user_email": user.email,
        })

    return {
        "items": items,
        "total_records": total,
        "page_no": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.delete("/transactions/{transaction_id}")
async def admin_delete_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    txn = await db.get(Transaction, transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    await db.delete(txn)
    await db.commit()

    await add_admin_log(db, current_admin, "DELETE_TRANSACTION", "transaction", transaction_id,
                        f"Deleted transaction {transaction_id}")

    return {"success": True, "message": "Transaction deleted successfully"}


# ═══════════════════════ ANALYTICS ═══════════════════════

@router.get("/analytics")
async def get_admin_analytics(
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    users_result = await db.execute(
        select(UserTableClass).where(func.lower(func.coalesce(UserTableClass.role, "user")) != "admin")
    )
    users = users_result.scalars().all()

    tx_result = await db.execute(select(Transaction))
    transactions = tx_result.scalars().all()

    growth_map = defaultdict(int)
    for user in users:
        if user.created_at:
            growth_map[user.created_at.strftime("%Y-%m")] += 1

    user_growth = [{"month": m, "users": c} for m, c in sorted(growth_map.items())]

    category_map = defaultdict(float)
    for txn in transactions:
        if (txn.type or "").lower() == "expense":
            category_map[txn.category or "Other"] += float(txn.amount or 0)

    category_distribution = [
        {"category": cat, "amount": amt}
        for cat, amt in sorted(category_map.items(), key=lambda x: x[1], reverse=True)
    ]

    user_spend_map = defaultdict(float)
    user_name_map = {u.id: u.name for u in users}

    for txn in transactions:
        if (txn.type or "").lower() == "expense":
            user_spend_map[txn.user_id] += float(txn.amount or 0)

    top_spending_users = [
        {"user_id": uid, "name": user_name_map.get(uid, "Unknown"), "expense": amt}
        for uid, amt in sorted(user_spend_map.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    total_expense = sum(float(t.amount or 0) for t in transactions if (t.type or "").lower() == "expense")
    months_count = max(len(user_growth), 1)

    return {
        "user_growth": user_growth,
        "category_distribution": category_distribution,
        "top_spending_users": top_spending_users,
        "average_monthly_spending": round(total_expense / months_count, 2),
    }


# ═══════════════════════ AI SUGGESTIONS ═══════════════════════

@router.get("/ai-suggestions")
async def admin_ai_suggestions(
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    users_result = await db.execute(
        select(UserTableClass).where(func.lower(func.coalesce(UserTableClass.role, "user")) != "admin")
    )
    users = users_result.scalars().all()

    tx_result = await db.execute(select(Transaction))
    transactions = tx_result.scalars().all()

    user_tx_map = defaultdict(list)
    for txn in transactions:
        user_tx_map[txn.user_id].append(txn)

    items = []
    for user in users:
        txs = user_tx_map.get(user.id, [])
        income = sum(float(t.amount or 0) for t in txs if (t.type or "").lower() == "income")
        expense = sum(float(t.amount or 0) for t in txs if (t.type or "").lower() == "expense")
        expense_ratio = round((expense / income) * 100, 1) if income > 0 else 0

        if income == 0 and expense > 0:
            suggestion = "Income data missing. Ask user to record income."
        elif expense_ratio >= 80:
            suggestion = "High expense ratio. Reduce discretionary spending."
        elif expense_ratio >= 50:
            suggestion = "Moderate spending. Improve monthly savings."
        else:
            suggestion = "Healthy spending pattern. Keep savings consistent."

        items.append({
            "user_id": user.id,
            "name": user.name,
            "email": user.email,
            "income": income,
            "expense": expense,
            "expense_ratio": expense_ratio,
            "suggestion": suggestion,
        })

    items.sort(key=lambda x: x["expense_ratio"], reverse=True)
    return {"items": items}


# ═══════════════════════ CATEGORIES ═══════════════════════

@router.get("/categories")
async def admin_get_categories(
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    result = await db.execute(select(Category).order_by(Category.type, Category.name))
    return result.scalars().all()


@router.post("/categories")
async def admin_create_category(
    payload: CategoryPayload,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    category = Category(name=payload.name.strip(), type=payload.type.strip().lower())
    db.add(category)
    await db.commit()
    await db.refresh(category)

    await add_admin_log(db, current_admin, "CREATE_CATEGORY", "category", category.id, f"Created {category.name}")
    return category


@router.patch("/categories/{category_id}")
async def admin_update_category(
    category_id: int,
    payload: CategoryUpdatePayload,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if payload.name is not None:
        category.name = payload.name.strip()
    if payload.type is not None:
        category.type = payload.type.strip().lower()

    await db.commit()
    await db.refresh(category)

    await add_admin_log(db, current_admin, "UPDATE_CATEGORY", "category", category.id, f"Updated {category.name}")
    return category


@router.delete("/categories/{category_id}")
async def admin_delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    category = await db.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    name = category.name
    await db.delete(category)
    await db.commit()

    await add_admin_log(db, current_admin, "DELETE_CATEGORY", "category", category_id, f"Deleted {name}")
    return {"success": True, "message": "Category deleted successfully"}


# ═══════════════════════ LOGS ═══════════════════════

@router.get("/logs")
async def get_admin_logs(
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_admin: UserTableClass = Depends(require_admin),
):
    result = await db.execute(
        select(AdminLog).order_by(desc(AdminLog.created_at)).limit(limit)
    )
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": log.id,
                "admin_id": log.admin_id,
                "action": log.action,
                "target_type": log.target_type,
                "target_id": log.target_id,
                "description": log.description,
                "created_at": log.created_at,
            }
            for log in logs
        ]
    }
