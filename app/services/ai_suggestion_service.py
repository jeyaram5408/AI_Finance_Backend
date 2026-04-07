from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.transaction_model import Transaction
from app.utils.finance_utils import compute_health

from google import genai
from pydantic import BaseModel, Field, ValidationError
from typing import Literal
import asyncio
import logging
import os


# --------------------------------------------------
# Logging
# --------------------------------------------------
logger = logging.getLogger(__name__)


# --------------------------------------------------
# Gemini client init
# --------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not set")

client = genai.Client(api_key=api_key)


# --------------------------------------------------
# Pydantic schema for strict JSON output
# --------------------------------------------------
class SuggestionItem(BaseModel):
    icon: str = Field(..., description="Single emoji only")
    title: str = Field(..., description="Short action title with specific ₹ amount")
    detail: str = Field(..., description="One sentence with exact category and ₹ values")
    priority: Literal["high", "medium", "low"]
    monthly_savings_potential: int = Field(..., ge=0)


class AIResponseSchema(BaseModel):
    summary: str
    suggestions: list[SuggestionItem]


# --------------------------------------------------
# Optional icon map for deterministic fallback
# --------------------------------------------------
CATEGORY_ICONS = {
    "food": "🍔",
    "dining": "🍽️",
    "groceries": "🛒",
    "shopping": "🛍️",
    "transport": "🚕",
    "travel": "✈️",
    "fuel": "⛽",
    "rent": "🏠",
    "home": "🏡",
    "utilities": "💡",
    "bills": "📄",
    "entertainment": "🎬",
    "subscriptions": "📺",
    "health": "💊",
    "medical": "🩺",
    "education": "📚",
    "emi": "💳",
    "loan": "🏦",
    "other": "💰",
}


# --------------------------------------------------
# Helpers
# --------------------------------------------------
def _priority_from_savings(amount: int) -> str:
    if amount > 1000:
        return "high"
    if 500 <= amount <= 1000:
        return "medium"
    return "low"


def _build_prompt(
    income: float,
    expense: float,
    savings: float,
    savings_rate: float,
    health_score: int,
    health_label: str,
    cat_lines: str,
) -> str:
    return f"""
You are an expert Indian personal finance advisor. Use ₹ for all amounts.

Monthly Financial Data:
- Income:       ₹{income:,.0f}
- Expense:      ₹{expense:,.0f}
- Savings:      ₹{savings:,.0f}
- Savings Rate: {savings_rate}%
- Health Score: {health_score}/100 ({health_label})

Expense Breakdown by Category:
{cat_lines}

Return valid JSON only.

Rules:
- Exactly 5 suggestions
- Avoid generic advice like "save more"
- Suggestions must be actionable and measurable
- Sort by priority: high → medium → low
- high   = saves more than ₹1000/month
- medium = saves ₹500–₹1000/month
- low    = saves less than ₹500/month
- monthly_savings_potential must be an integer
- Reference actual category names and ₹ values from the data above
- summary must be 2 sentences
- Be practical, specific, and honest
- Avoid markdown
""".strip()


def _generate_with_gemini(prompt: str) -> AIResponseSchema:
    """
    Sync helper; call via asyncio.to_thread from async code.
    """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config={
            "temperature": 0.5,
            "response_mime_type": "application/json",
            "response_json_schema": AIResponseSchema.model_json_schema(),
        },
    )

    raw_text = (response.text or "").strip()
    if not raw_text:
        raise ValueError("Empty response from Gemini")

    return AIResponseSchema.model_validate_json(raw_text)


def _build_fallback_ai_response(
    income: float,
    expense: float,
    savings: float,
    savings_rate: float,
    sorted_cats: list[tuple[str, float]],
) -> AIResponseSchema:
    """
    Deterministic fallback so the app still returns useful suggestions
    even if Gemini fails.
    """
    suggestions: list[SuggestionItem] = []

    for cat, amt in sorted_cats[:5]:
        cat_clean = cat.strip().lower() if cat else "other"
        icon = CATEGORY_ICONS.get(cat_clean, "💰")

        if amt >= 10000:
            cut_pct = 0.15
        elif amt >= 5000:
            cut_pct = 0.12
        elif amt >= 2500:
            cut_pct = 0.10
        else:
            cut_pct = 0.07

        potential = max(100, int(round(amt * cut_pct)))
        priority = _priority_from_savings(potential)

        suggestions.append(
            SuggestionItem(
                icon=icon,
                title=f"Cut {cat_clean.capitalize()} ₹{potential}",
                detail=(
                    f"{cat_clean.capitalize()} spending is ₹{amt:,.0f}; aim to reduce it by about "
                    f"₹{potential:,.0f} per month to improve savings with minimal lifestyle impact."
                ),
                priority=priority,
                monthly_savings_potential=potential,
            )
        )

    # Fill to exactly 5 suggestions if categories are fewer
    filler_pool = [
        SuggestionItem(
            icon="💸",
            title="Track daily cash ₹300",
            detail="Review small daily spends and cut around ₹300 per month from low-value purchases to reduce leakage.",
            priority="low",
            monthly_savings_potential=300,
        ),
        SuggestionItem(
            icon="🏦",
            title="Auto-save ₹500",
            detail="Automate a ₹500 monthly transfer to savings immediately after income is credited to build discipline.",
            priority="medium",
            monthly_savings_potential=500,
        ),
        SuggestionItem(
            icon="📱",
            title="Review subscriptions ₹400",
            detail="Audit recurring app and subscription payments and cancel low-use services to save about ₹400 monthly.",
            priority="low",
            monthly_savings_potential=400,
        ),
        SuggestionItem(
            icon="🛍️",
            title="Plan impulse buys ₹750",
            detail="Set a cooling-off rule for non-essential purchases and reduce unplanned spending by around ₹750 monthly.",
            priority="medium",
            monthly_savings_potential=750,
        ),
        SuggestionItem(
            icon="📊",
            title="Weekly budget check ₹600",
            detail="Do a weekly spending review and cap avoidable overages to save roughly ₹600 per month.",
            priority="medium",
            monthly_savings_potential=600,
        ),
    ]

    i = 0
    while len(suggestions) < 5 and i < len(filler_pool):
        suggestions.append(filler_pool[i])
        i += 1

    priority_order = {"high": 1, "medium": 2, "low": 3}
    suggestions.sort(key=lambda x: priority_order.get(x.priority, 3))

    summary = (
        f"Your total income is ₹{income:,.0f}, expenses are ₹{expense:,.0f}, and savings are ₹{savings:,.0f}. "
        f"Your savings rate is {savings_rate}%, so improving your top spending categories should strengthen your monthly cash flow."
    )

    return AIResponseSchema(summary=summary, suggestions=suggestions[:5])


# --------------------------------------------------
# Main service function
# --------------------------------------------------
async def generate_ai_suggestions(db: AsyncSession, user_id: int):
    # 1) Fetch transactions
    result = await db.execute(
        select(Transaction).where(Transaction.user_id == user_id)
    )
    transactions = result.scalars().all()

    if not transactions:
        return {
            "suggestions": [],
            "summary": "No transaction data found. Please add some transactions first.",
            "health_score": 0,
            "health_label": "No Data",
            "savings_rate": 0,
            "budget_50_30_20": {"needs": 0, "wants": 0, "savings": 0},
            "income": 0,
            "expense": 0,
            "savings": 0,
        }

    # 2) Calculate totals
    income = 0.0
    expense = 0.0
    category_map: dict[str, float] = {}

    for t in transactions:
        amount = float(t.amount or 0)
        t_type = (t.type or "").strip().lower()
        cat = (t.category or "other").strip().lower()

        if t_type == "income":
            income += amount
        else:
            expense += amount
            category_map[cat] = category_map.get(cat, 0.0) + amount

    savings = income - expense
    savings_rate = round((savings / income * 100), 1) if income > 0 else 0
    health_score, health_label = compute_health(income, savings)

    # 3) Category breakdown
    sorted_cats = sorted(category_map.items(), key=lambda x: -x[1])

    if sorted_cats:
        cat_lines = "\n".join(
            f"  - {cat.capitalize()}: ₹{amt:,.0f} ({(amt / expense * 100) if expense > 0 else 0:.1f}% of expenses)"
            for cat, amt in sorted_cats
        )
    else:
        cat_lines = "  - No category breakdown available"

    # 4) Build prompt
    prompt = _build_prompt(
        income=income,
        expense=expense,
        savings=savings,
        savings_rate=savings_rate,
        health_score=health_score,
        health_label=health_label,
        cat_lines=cat_lines,
    )

    # 5) Call Gemini with structured output
    try:
        ai_data = await asyncio.wait_for(
            asyncio.to_thread(_generate_with_gemini, prompt),
            timeout=12
)
        suggestions = ai_data.suggestions[:5]
        priority_order = {"high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda x: priority_order.get(x.priority, 3))

    except (ValidationError, ValueError, Exception) as e:
        logger.exception("Gemini AI suggestion generation failed: %s", e)
        ai_data = _build_fallback_ai_response(
            income=income,
            expense=expense,
            savings=savings,
            savings_rate=savings_rate,
            sorted_cats=sorted_cats,
        )
        suggestions = ai_data.suggestions[:5]

    # 6) Final response
    return {
        "income": round(income, 2),
        "expense": round(expense, 2),
        "savings": round(savings, 2),
        "savings_rate": savings_rate,
        "health_score": health_score,
        "health_label": health_label,
        "budget_50_30_20": {
            "needs": round(income * 0.50),
            "wants": round(income * 0.30),
            "savings": round(income * 0.20),
        },
        "summary": ai_data.summary,
        "suggestions": [item.model_dump() for item in suggestions],
    }
