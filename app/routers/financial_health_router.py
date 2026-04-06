from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.dependencies.auth_dependency import get_current_user
from app.models.transaction_model import Transaction
from app.models.user_table_model import UserTableClass

from sqlalchemy import select
from collections import defaultdict
from statistics import pstdev
from datetime import datetime

from google import genai

import os
import json
import re

router = APIRouter(prefix="/financial-health", tags=["Financial Health"])

# ─────────────────────────────────────────────────────────────
# GEMINI INIT
# ─────────────────────────────────────────────────────────────
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not set in environment variables")

# genai.configure(api_key=api_key)response = model.generate_content(prompt)

# model = genai.GenerativeModel("gemini-1.5-flash")
client = genai.Client(api_key=api_key)

# ─────────────────────────────────────────────────────────────
# CATEGORY RULES
# ─────────────────────────────────────────────────────────────
WANTS_KEYWORDS = {
    "shopping", "entertainment", "movie", "movies", "food", "dining",
    "restaurant", "travel", "trip", "luxury", "subscriptions", "subscription",
    "games", "gaming", "swiggy", "zomato", "fun", "outing", "snacks", "cafe",
}

NEEDS_KEYWORDS = {
    "rent", "emi", "loan", "groceries", "grocery", "medical", "medicine",
    "insurance", "electricity", "water", "fuel", "petrol", "diesel",
    "transport", "internet", "wifi", "education", "school", "college",
    "hospital", "utility", "utilities",
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def clamp(val, low, high):
    return max(low, min(high, val))


def score_to_label(score: int):
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Fair"
    if score >= 35:
        return "Poor"
    return "Critical"


def normalize_category(cat: str) -> str:
    return (cat or "other").strip().lower()


def is_wants_category(cat: str) -> bool:
    cat = normalize_category(cat)
    return any(keyword in cat for keyword in WANTS_KEYWORDS)


def is_needs_category(cat: str) -> bool:
    cat = normalize_category(cat)
    return any(keyword in cat for keyword in NEEDS_KEYWORDS)


def safe_date_key(dt_obj):
    if not dt_obj:
        return None
    if isinstance(dt_obj, datetime):
        return dt_obj.strftime("%Y-%m")
    try:
        return dt_obj.strftime("%Y-%m")
    except Exception:
        return None


def get_transaction_owner_field():
    if hasattr(Transaction, "user_id"):
        return getattr(Transaction, "user_id")
    if hasattr(Transaction, "usertable_id"):
        return getattr(Transaction, "usertable_id")
    return None


def build_monthly_series(transactions):
    monthly_income = defaultdict(float)
    monthly_expense = defaultdict(float)

    for t in transactions:
        tx_date = getattr(t, "date", None) or getattr(t, "created_at", None)
        month_key = safe_date_key(tx_date)
        if not month_key:
            continue

        amount = float(getattr(t, "amount", 0) or 0)
        tx_type = (getattr(t, "type", "") or "").lower()

        if tx_type == "income":
            monthly_income[month_key] += amount
        else:
            monthly_expense[month_key] += amount

    all_months = sorted(set(monthly_income.keys()) | set(monthly_expense.keys()))
    income_series = [monthly_income[m] for m in all_months]
    expense_series = [monthly_expense[m] for m in all_months]

    return all_months, income_series, expense_series


def compute_stability_score(monthly_expense_series):
    if not monthly_expense_series:
        return 5, 0
    if len(monthly_expense_series) == 1:
        return 6, 0

    avg_exp = sum(monthly_expense_series) / len(monthly_expense_series)
    if avg_exp <= 0:
        return 5, 0

    volatility = pstdev(monthly_expense_series) / avg_exp

    if volatility <= 0.10:
        return 10, round(volatility * 100, 1)
    if volatility <= 0.20:
        return 8, round(volatility * 100, 1)
    if volatility <= 0.35:
        return 5, round(volatility * 100, 1)
    return 2, round(volatility * 100, 1)


def compute_financial_health(
    profile_income: float,
    transaction_income: float,
    expense: float,
    category_map: dict,
    savings_goal: float | None,
    monthly_expense_series: list[float] | None = None,
):
    income = max(transaction_income, profile_income, 0)
    savings = income - expense
    savings_rate = round((savings / income * 100), 1) if income > 0 else 0
    expense_ratio = round((expense / income * 100), 1) if income > 0 else 100

    # 1) Savings Rate Score /30
    if savings_rate >= 30:
        savings_rate_score = 30
    elif savings_rate >= 20:
        savings_rate_score = 24
    elif savings_rate >= 10:
        savings_rate_score = 16
    elif savings_rate >= 0:
        savings_rate_score = 8
    else:
        savings_rate_score = 0

    # 2) Expense Control Score /20
    if expense_ratio <= 50:
        expense_control_score = 20
    elif expense_ratio <= 70:
        expense_control_score = 15
    elif expense_ratio <= 90:
        expense_control_score = 8
    else:
        expense_control_score = 2

    # 3) Top Category Concentration /15
    top_category = None
    top_category_amount = 0
    top_category_share = 0

    if expense > 0 and category_map:
        top_category, top_category_amount = max(category_map.items(), key=lambda x: x[1])
        top_category_share = round((top_category_amount / expense) * 100, 1)

    if top_category_share <= 25:
        category_score = 15
    elif top_category_share <= 40:
        category_score = 11
    elif top_category_share <= 55:
        category_score = 6
    else:
        category_score = 2

    # 4) Wants Overspend Score /15
    wants_total = 0
    needs_total = 0

    for cat, amt in category_map.items():
        if is_wants_category(cat):
            wants_total += amt
        elif is_needs_category(cat):
            needs_total += amt

    wants_ratio = round((wants_total / expense) * 100, 1) if expense > 0 else 0
    needs_ratio = round((needs_total / expense) * 100, 1) if expense > 0 else 0

    if wants_ratio <= 20:
        wants_score = 15
    elif wants_ratio <= 35:
        wants_score = 10
    elif wants_ratio <= 50:
        wants_score = 5
    else:
        wants_score = 1

    # 5) Savings Goal Progress /10
    goal_progress = None
    if savings_goal and savings_goal > 0:
        goal_progress = round((savings / savings_goal) * 100, 1) if savings > 0 else 0

        if goal_progress >= 100:
            goal_score = 10
        elif goal_progress >= 75:
            goal_score = 8
        elif goal_progress >= 50:
            goal_score = 6
        elif goal_progress > 0:
            goal_score = 3
        else:
            goal_score = 0
    else:
        goal_score = 5

    # 6) Expense Stability /10
    stability_score, expense_volatility = compute_stability_score(monthly_expense_series or [])

    base_score = (
        savings_rate_score
        + expense_control_score
        + category_score
        + wants_score
        + goal_score
        + stability_score
    )
    base_score = int(clamp(round(base_score), 0, 100))

    data_confidence = "high"
    if income > 0 and expense == 0:
        base_score = min(base_score, 55)
        data_confidence = "low"
    elif income == 0 and expense > 0:
        data_confidence = "medium"

    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "savings": round(savings, 2),
        "savings_rate": savings_rate,
        "expense_ratio": expense_ratio,
        "top_category": top_category,
        "top_category_amount": round(top_category_amount, 2),
        "top_category_share": top_category_share,
        "wants_spend": round(wants_total, 2),
        "wants_ratio": wants_ratio,
        "needs_spend": round(needs_total, 2),
        "needs_ratio": needs_ratio,
        "goal_progress": goal_progress,
        "expense_volatility": expense_volatility,
        "data_confidence": data_confidence,
        "base_score": base_score,
        "base_label": score_to_label(base_score),
        "score_breakdown": {
            "savings_rate_score": savings_rate_score,
            "expense_control_score": expense_control_score,
            "category_score": category_score,
            "wants_score": wants_score,
            "goal_score": goal_score,
            "stability_score": stability_score,
        },
        "budget_50_30_20": {
            "needs": round(income * 0.50, 2),
            "wants": round(income * 0.30, 2),
            "savings": round(income * 0.20, 2),
        }
    }


def extract_json(raw: str):
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()

    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                return {}
    return {}


# ─────────────────────────────────────────────────────────────
# ROUTE
# ─────────────────────────────────────────────────────────────
@router.get("/")
async def get_financial_health(
    db: AsyncSession = Depends(get_db),
    current_user: UserTableClass = Depends(get_current_user)
):
    owner_field = get_transaction_owner_field()
    if owner_field is None:
        return {
            "success": False,
            "message": "Transaction model must contain user_id or usertable_id field",
            "data": None
        }

    result = await db.execute(
        select(Transaction).where(owner_field == current_user.id)
    )
    transactions = result.scalars().all()

    profile_income = float(getattr(current_user, "monthly_income", 0) or 0)
    savings_goal = float(getattr(current_user, "savings_goal", 0) or 0)

    if not transactions and profile_income <= 0:
        return {
            "success": True,
            "message": "No data available",
            "data": {
                "income": 0,
                "expense": 0,
                "savings": 0,
                "savings_rate": 0,
                "expense_ratio": 0,
                "base_score": 0,
                "ai_adjustment": 0,
                "final_score": 0,
                "health_label": "No Data",
                "summary": "No transaction data or profile income found. Add monthly income and track transactions to generate your financial health score.",
                "strengths": [],
                "risks": ["Financial health cannot be measured without enough user data."],
                "actions": [
                    "Update your monthly income in profile",
                    "Add your expense transactions",
                    "Set a monthly savings goal"
                ],
                "score_breakdown": {},
                "category_breakdown": {},
                "budget_50_30_20": {"needs": 0, "wants": 0, "savings": 0}
            }
        }

    transaction_income = 0.0
    expense = 0.0
    category_map = defaultdict(float)

    for t in transactions:
        amount = float(getattr(t, "amount", 0) or 0)
        tx_type = (getattr(t, "type", "") or "").lower()
        cat = normalize_category(getattr(t, "category", "other"))

        if tx_type == "income":
            transaction_income += amount
        else:
            expense += amount
            category_map[cat] += amount

    months_analyzed, monthly_income_series, monthly_expense_series = build_monthly_series(transactions)

    metrics = compute_financial_health(
        profile_income=profile_income,
        transaction_income=transaction_income,
        expense=expense,
        category_map=dict(category_map),
        savings_goal=savings_goal,
        monthly_expense_series=monthly_expense_series,
    )

    sorted_categories = sorted(category_map.items(), key=lambda x: -x[1])

    category_lines = "\n".join(
        f"- {cat.capitalize()}: ₹{amt:,.0f}"
        for cat, amt in sorted_categories
    ) if sorted_categories else "- No expense categories"

    prompt = f"""
You are an expert Indian personal finance advisor.

Analyze the user's structured financial data and return ONLY valid JSON.

User Financial Data:
- Income Used For Score: ₹{metrics['income']:,.0f}
- Profile Monthly Income: ₹{profile_income:,.0f}
- Transaction Income: ₹{transaction_income:,.0f}
- Expense: ₹{metrics['expense']:,.0f}
- Savings: ₹{metrics['savings']:,.0f}
- Savings Rate: {metrics['savings_rate']}%
- Expense Ratio: {metrics['expense_ratio']}%
- Top Category: {metrics['top_category']}
- Top Category Amount: ₹{metrics['top_category_amount']:,.0f}
- Top Category Share: {metrics['top_category_share']}%
- Wants Spend: ₹{metrics['wants_spend']:,.0f}
- Wants Ratio: {metrics['wants_ratio']}%
- Needs Spend: ₹{metrics['needs_spend']:,.0f}
- Needs Ratio: {metrics['needs_ratio']}%
- Savings Goal: ₹{savings_goal:,.0f}
- Goal Progress: {metrics['goal_progress']}
- Expense Volatility: {metrics['expense_volatility']}%
- Base Score: {metrics['base_score']}/100
- Base Label: {metrics['base_label']}
- Data Confidence: {metrics['data_confidence']}

Expense Categories:
{category_lines}

Score Breakdown:
{json.dumps(metrics['score_breakdown'], indent=2)}

Return exact JSON only:
{{
  "summary": "2 short sentences with exact ₹ amounts where useful",
  "strengths": ["point 1", "point 2"],
  "risks": ["point 1", "point 2"],
  "actions": ["action 1", "action 2", "action 3"],
  "ai_adjustment": 0,
  "adjustment_reason": "one short sentence"
}}

Rules:
- ai_adjustment must be an integer between -5 and +5
- Use actual category names where relevant
- Keep suggestions practical and specific
- No markdown, return pure JSON only
"""

    ai_data = {
        "summary": "",
        "strengths": [],
        "risks": [],
        "actions": [],
        "ai_adjustment": 0,
        "adjustment_reason": ""
    }

    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )      
        raw = response.text.strip()
        parsed = extract_json(raw)

        if isinstance(parsed, dict):
            ai_data = {
                "summary": parsed.get("summary", ""),
                "strengths": parsed.get("strengths", []) if isinstance(parsed.get("strengths", []), list) else [],
                "risks": parsed.get("risks", []) if isinstance(parsed.get("risks", []), list) else [],
                "actions": parsed.get("actions", []) if isinstance(parsed.get("actions", []), list) else [],
                "ai_adjustment": parsed.get("ai_adjustment", 0),
                "adjustment_reason": parsed.get("adjustment_reason", ""),
            }
    except Exception as e:
        print("🔥 Gemini Financial Health Error:", e)

    try:
        ai_adjustment = int(ai_data.get("ai_adjustment", 0))
    except Exception:
        ai_adjustment = 0

    ai_adjustment = clamp(ai_adjustment, -5, 5)
    final_score = int(clamp(metrics["base_score"] + ai_adjustment, 0, 100))
    health_label = score_to_label(final_score)

    if not ai_data.get("summary"):
        ai_data["summary"] = (
            f"Your current monthly income is ₹{metrics['income']:,.0f} and monthly expenses are ₹{metrics['expense']:,.0f}. "
            f"Your estimated savings are ₹{metrics['savings']:,.0f}, resulting in a financial health score of {final_score}/100."
        )

    return {
        "success": True,
        "message": "Financial health calculated successfully",
        "data": {
            **metrics,
            "profile_income": round(profile_income, 2),
            "transaction_income": round(transaction_income, 2),
            "savings_goal": round(savings_goal, 2),
            "months_analyzed": months_analyzed,
            "ai_adjustment": ai_adjustment,
            "final_score": final_score,
            "health_label": health_label,
            "summary": ai_data.get("summary", ""),
            "strengths": ai_data.get("strengths", [])[:3],
            "risks": ai_data.get("risks", [])[:3],
            "actions": ai_data.get("actions", [])[:5],
            "adjustment_reason": ai_data.get("adjustment_reason", ""),
            "category_breakdown": dict(sorted_categories),
        }
    }