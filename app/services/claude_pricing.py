"""
Claude-powered dynamic reward pricing.

Called every time a user checks their reward estimate.
Returns multiplier + plain-English reason (shown in UI).

Model: claude-haiku  — fast (~1s) and cheap enough for per-request calls.
Fallback: if Claude is unavailable, a simple formula runs instead so the
app never breaks.
"""
import json
import httpx
from app.core.config import settings


SYSTEM_PROMPT = """You are the reward pricing engine for Namma EcoExchange, 
a platform in Bengaluru that converts organic wet waste into biogas cylinders.
Your job: given the current state of a biogas plant and a user's quality rating,
decide how many Green Points to award per kg of organic waste deposited.

Rules:
- Base rate is 10 pts/kg. You output a multiplier (0.5 to 3.0) applied to this base.
- Low plant fill + high demand = higher multiplier (city urgently needs more waste input).
- High plant fill + low demand = lower multiplier (plant is near capacity, slow intake).
- User rating boosts: 4.5-5.0 → +0.3x, 4.0-4.4 → +0.2x, 3.0-3.9 → +0.1x, below 3.0 → no bonus.
- Always keep the reason short (1 sentence), friendly, and actionable.
- Respond ONLY with valid JSON. No preamble, no markdown."""

USER_TEMPLATE = """Plant fill: {fill_pct}% of daily capacity
Demand level: {demand_level}
User rating: {user_rating}/5.0

Return JSON: {{"multiplier": <float 0.5-3.0>, "reason": "<1 sentence>"}}"""


async def get_ai_multiplier(
    fill_pct: float,
    demand_level: str,
    user_rating: float,
) -> dict:
    """
    Returns {"multiplier": float, "reason": str}
    Falls back to formula if Claude call fails.
    """
    prompt = USER_TEMPLATE.format(
        fill_pct=round(fill_pct, 1),
        demand_level=demand_level,
        user_rating=user_rating,
    )

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 120,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"].strip()
        result = json.loads(text)
        return {
            "multiplier": float(max(0.5, min(3.0, result["multiplier"]))),
            "reason": result.get("reason", ""),
        }

    except Exception as e:
        # Fallback formula — app never breaks even if Claude is down
        return _fallback_multiplier(fill_pct, demand_level, user_rating)


def _fallback_multiplier(fill_pct: float, demand_level: str, user_rating: float) -> dict:
    m = 1.0
    if fill_pct < 30:   m += 0.6
    elif fill_pct < 60: m += 0.3
    elif fill_pct > 85: m -= 0.3

    if demand_level == "high":   m += 0.4
    elif demand_level == "low":  m -= 0.1

    if user_rating >= 4.5:   m += 0.3
    elif user_rating >= 4.0: m += 0.2
    elif user_rating >= 3.0: m += 0.1

    m = round(max(0.5, min(3.0, m)), 2)
    return {
        "multiplier": m,
        "reason": f"Plant is {round(fill_pct)}% full with {demand_level} demand — your {user_rating}/5 rating earns a {m}x multiplier.",
    }
