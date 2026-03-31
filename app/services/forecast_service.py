from sqlalchemy import select, func
from app.models.transaction_model import Transaction


async def get_monthly_expenses(db, user_id: int):
    result = await db.execute(
        select(
            func.date_format(Transaction.date, "%Y-%m").label("month"),
            func.sum(Transaction.amount).label("total_expense")
        )
        .where(
            Transaction.user_id == user_id,
            Transaction.type == "expense"
        )
        .group_by(func.date_format(Transaction.date, "%Y-%m"))
        .order_by(func.date_format(Transaction.date, "%Y-%m"))
    )

    rows = result.all()

    return [
        {
            "month": r.month,
            "total_expense": float(r.total_expense or 0)
        }
        for r in rows
    ]


def calculate_forecast(monthly_data):
    if not monthly_data:
        return {
            "monthly_avg": 0,
            "next_month": 0,
            "six_month": 0
        }

    values = [m["total_expense"] for m in monthly_data]
    avg = sum(values) / len(values)

    return {
        "monthly_avg": avg,
        "next_month": avg,
        "six_month": avg * 6
    }
