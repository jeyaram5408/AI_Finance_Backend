from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.transaction_model import Transaction
from app.utils.finance_utils import compute_health

from groq import Groq
import os
import re
import json


# ── Groq client init ──
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY not set")

client = Groq(api_key=api_key)


# ── MAIN SERVICE FUNCTION ──
async def generate_ai_suggestions(db: AsyncSession, user_id: int):
    # ── 1. Fetch transactions ──
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
            "budget_50_30_20": {"needs": 0, "wants": 0, "savings": 0}
        }

    # ── 2. Calculate totals ──
    income = 0.0
    expense = 0.0
    category_map = {}

    for t in transactions:
        amount = float(t.amount or 0)
        t_type = (t.type or "").lower()
        cat = (t.category or "other").lower()

        if t_type == "income":
            income += amount
        else:
            expense += amount
            category_map[cat] = category_map.get(cat, 0) + amount

    savings = income - expense
    savings_rate = round((savings / income * 100), 1) if income > 0 else 0
    health_score, health_label = compute_health(income, savings)

    # ── 3. Category breakdown ──
    sorted_cats = sorted(category_map.items(), key=lambda x: -x[1])

    cat_lines = "\n".join(
        f"  - {cat.capitalize()}: ₹{amt:,.0f}  ({(amt / expense * 100) if expense > 0 else 0:.1f}% of expenses)"
        for cat, amt in sorted_cats
    ) if sorted_cats else "  - No category breakdown available"

    # ── 4. AI Prompt ──
    prompt = f"""You are an expert Indian personal finance advisor. Use ₹ for all amounts.

Monthly Financial Data:
- Income:       ₹{income:,.0f}
- Expense:      ₹{expense:,.0f}
- Savings:      ₹{savings:,.0f}
- Savings Rate: {savings_rate}%
- Health Score: {health_score}/100 ({health_label})

Expense Breakdown by Category:
{cat_lines}

Return ONLY this exact JSON (no markdown, no explanation):
{{
  "summary": "2 sentences. Mention specific ₹ amounts. Honest assessment.",
  "suggestions": [
    {{
      "icon": "single emoji",
      "title": "Action title with specific ₹ (max 7 words)",
      "detail": "One sentence with exact category name and ₹ amounts — what to cut, by how much, why.",
      "priority": "high",
      "monthly_savings_potential": 3000
    }}
  ]
}}

Rules:
- Exactly 5 suggestions
- Sort by priority: high → medium → low
- high   = saves more than ₹1000/month
- medium = saves ₹500–₹1000/month
- low    = saves less than ₹500/month
- monthly_savings_potential must be a number (integer)
- Reference actual category names and ₹ values from the data above"""

    # ── 5. Call AI ──
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw = response.choices[0].message.content.strip()
    except Exception as e:
        print("🔥 Groq Error:", e)
        raw = ""

    # ── 6. Parse AI Response ──
    try:
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()

        ai_data = json.loads(raw)

        # Validate structure
        if "suggestions" not in ai_data or not isinstance(ai_data["suggestions"], list):
            ai_data["suggestions"] = []

        if "summary" not in ai_data:
            ai_data["summary"] = "AI analysis unavailable"

        # Limit + sort
        suggestions = ai_data["suggestions"][:5]

        priority_order = {"high": 1, "medium": 2, "low": 3}
        suggestions.sort(
            key=lambda x: priority_order.get(x.get("priority", "low"), 3)
        )

    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            ai_data = json.loads(match.group())
            suggestions = ai_data.get("suggestions", [])
        else:
            ai_data = {
                "summary": "Analysis complete. Please review your spending.",
                "suggestions": []
            }
            suggestions = []

    # ── 7. Final response ──
    return {
        "income": income,
        "expense": expense,
        "savings": savings,
        "savings_rate": savings_rate,
        "health_score": health_score,
        "health_label": health_label,
        "budget_50_30_20": {
            "needs": round(income * 0.50),
            "wants": round(income * 0.30),
            "savings": round(income * 0.20),
        },
        "summary": ai_data.get("summary", ""),
        "suggestions": suggestions,
    }