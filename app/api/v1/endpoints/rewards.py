"""
/rewards/preview  — user enters kg, gets back estimated points (Claude-powered)
/rewards/history  — time-series of multipliers for the graph
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import User, BiogasPlant, RewardPreview
from app.schemas.schemas import (
    RewardPreviewRequest, RewardPreviewResponse,
    PricingHistoryPoint, PricingHistoryResponse,
)
from app.services.claude_pricing import get_ai_multiplier
from app.core.config import settings

router = APIRouter(prefix="/rewards", tags=["Rewards"])


async def _get_user_and_plant(user_id: int, db: AsyncSession):
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # biogas_plant field stores plant id as string
    try:
        plant_id = int(user.biogas_plant)
    except (ValueError, TypeError):
        raise HTTPException(400, "User is not linked to a valid biogas plant")

    plant_res = await db.execute(select(BiogasPlant).where(BiogasPlant.id == plant_id))
    plant = plant_res.scalar_one_or_none()
    if not plant:
        raise HTTPException(404, "Linked biogas plant not found")

    return user, plant


def _user_rating(user: User) -> float:
    """loyalty_score is stored as e.g. 48 meaning 4.8 — convert to float rating."""
    if user.loyalty_score is None:
        return 3.0
    return round(user.loyalty_score / 10, 1)


# ── Preview endpoint ─────────────────────────────────────────────────────────

@router.post("/{user_id}/preview", response_model=RewardPreviewResponse)
async def preview_reward(
    user_id: int,
    payload: RewardPreviewRequest,
    db: AsyncSession = Depends(get_db),
):
    user, plant = await _get_user_and_plant(user_id, db)

    fill_pct = (
        round((plant.current_input_kg or 0) / plant.capacity * 100, 1)
        if plant.capacity else 0.0
    )
    rating = _user_rating(user)

    ai = await get_ai_multiplier(fill_pct, plant.demand, rating)
    multiplier = ai["multiplier"]
    points_estimate = round(payload.weight_kg * settings.base_points_per_kg * multiplier)

    preview = RewardPreview(
        user_id=user.id,
        plant_id=plant.id,
        weight_kg=payload.weight_kg,
        multiplier=multiplier,
        points_estimate=points_estimate,
        plant_fill_pct=fill_pct,
        user_rating=rating,
        demand_level=plant.demand,
        ai_reason=ai["reason"],
    )
    db.add(preview)
    await db.flush()
    return preview


# ── Graph endpoint ────────────────────────────────────────────────────────────

@router.get("/{user_id}/history", response_model=PricingHistoryResponse)
async def pricing_history(
    user_id: int,
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    user, plant = await _get_user_and_plant(user_id, db)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(RewardPreview)
        .where(
            RewardPreview.user_id == user_id,
            RewardPreview.created_at >= since,
        )
        .order_by(RewardPreview.created_at.asc())
    )
    rows = result.scalars().all()

    history = [
        PricingHistoryPoint(
            timestamp=r.created_at,
            multiplier=r.multiplier,
            points_per_kg=round(r.multiplier * settings.base_points_per_kg, 1),
            plant_fill_pct=r.plant_fill_pct,
            demand_level=r.demand_level,
        )
        for r in rows
    ]

    fill_pct = (
        round((plant.current_input_kg or 0) / plant.capacity * 100, 1)
        if plant.capacity else 0.0
    )
    rating = _user_rating(user)
    ai = await get_ai_multiplier(fill_pct, plant.demand, rating)
    current_multi = ai["multiplier"]

    return PricingHistoryResponse(
        user_rating=rating,
        history=history,
        current_multiplier=current_multi,
        current_points_per_kg=round(current_multi * settings.base_points_per_kg, 1),
    )