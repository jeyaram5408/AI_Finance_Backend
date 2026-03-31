from sqlalchemy import select
from app.models.transaction_model import Transaction


async def get_dashboard_data(db, user_id: int):
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    )
    transactions = result.scalars().all()

    income = 0.0
    expense = 0.0
    category_map = {}

    for t in transactions:
        amount = float(t.amount or 0)

        if (t.type or "").lower() == "income":
            income += amount
        else:
            expense += amount
            cat = (t.category or "Other").strip()
            category_map[cat] = category_map.get(cat, 0) + amount

    savings = income - expense
    score = round(max(0, min(100, (savings / income) * 100))) if income > 0 else 0

    chart_data = [
        {"name": k, "value": v}
        for k, v in category_map.items()
    ]

    return {
        "income": income,
        "expense": expense,
        "savings": savings,
        "score": score,
        "chartData": chart_data
    }
