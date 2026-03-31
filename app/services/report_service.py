from sqlalchemy import select
from app.models.transaction_model import Transaction
from collections import defaultdict
from datetime import datetime, timedelta, date


async def get_report_data(db, user_id: int, start_date=None, end_date=None, category=None, type=None):
    today = datetime.now()

    if not start_date and not end_date:
        end = today
        start = end - timedelta(days=180)
    else:
        try:
            start = datetime.fromisoformat(start_date) if start_date else None
            end = datetime.fromisoformat(end_date) if end_date else None
        except Exception:
            return {"summary": {}, "chart": [], "forecast": {}}

    if start and end and start > end:
        return {"summary": {}, "chart": [], "forecast": {}}

    if start and start > today:
        return {"summary": {}, "chart": [], "forecast": {}}

    if end and end > today:
        end = today

    query = select(Transaction).where(Transaction.user_id == user_id)
    result = await db.execute(query)
    transactions = result.scalars().all()

    filtered = []
    for tx in transactions:
        tx_date = tx.date
        if isinstance(tx_date, date):
            tx_dt = datetime.combine(tx_date, datetime.min.time())
        else:
            try:
                tx_dt = datetime.fromisoformat(str(tx_date))
            except Exception:
                continue

        if start and tx_dt < start:
            continue
        if end and tx_dt > end:
            continue
        if category and tx.category != category:
            continue
        if type and tx.type.lower() != type.lower():
            continue

        filtered.append(tx)

    if not filtered:
        return {"summary": {}, "chart": [], "forecast": {}}

    total_income = 0.0
    total_expense = 0.0

    monthly_map = defaultdict(lambda: {
        "month": "",
        "income": 0,
        "expense": 0,
        "full_date": ""
    })

    for tx in filtered:
        amount = max(float(tx.amount), 0)
        tx_type = tx.type.lower()

        if tx_type == "income":
            total_income += amount
        else:
            total_expense += amount

        d = tx.date
        if isinstance(d, date):
            key = d.strftime("%Y-%m")
            month_name = d.strftime("%b")
        else:
            d = datetime.fromisoformat(str(d))
            key = d.strftime("%Y-%m")
            month_name = d.strftime("%b")

        monthly_map[key]["month"] = month_name
        monthly_map[key]["full_date"] = key

        if tx_type == "income":
            monthly_map[key]["income"] += amount
        else:
            monthly_map[key]["expense"] += amount

    savings = total_income - total_expense
    expense_ratio = (total_expense / total_income * 100) if total_income else 0
    savings_rate = (savings / total_income * 100) if total_income else 0
    score = int(max(0, min((1 - (total_expense / total_income)) * 100 if total_income else 0, 100)))

    months = len(monthly_map) if monthly_map else 1
    monthly_avg = total_expense / months
    next_month = monthly_avg * 1.05
    six_month = monthly_avg * 6

    chart_data = sorted(monthly_map.values(), key=lambda x: x["full_date"])

    return {
        "summary": {
            "income": total_income,
            "expense": total_expense,
            "savings": savings,
            "score": score,
            "expense_ratio": expense_ratio,
            "savings_rate": savings_rate
        },
        "chart": chart_data,
        "forecast": {
            "monthly_avg": monthly_avg,
            "next_month": next_month,
            "six_month": six_month
        }
    }
