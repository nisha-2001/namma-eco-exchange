from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app import db
from app.db.database import get_db
from app.models.models import User, UserTransaction, BiogasPlant
from app.schemas.schemas import UserCreate, UserResponse, TransactionResponse, CalculateRewardResponse, CalculateRewardRequest
from app.utils.reward_calculator import calculate_reward

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "Email already registered")
    user = User(**payload.model_dump())
    db.add(user)
    await db.flush()
    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("/{user_id}/transactions", response_model=list[TransactionResponse])
async def get_transactions(
    user_id: int,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserTransaction)
        .where(UserTransaction.user_id == user_id)
        .order_by(UserTransaction.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

# ── New: calculate reward ─────────────────────────────────────────────────────

@router.post("/calculate-reward", response_model=CalculateRewardResponse)
async def calculate_reward_endpoint(
    payload: CalculateRewardRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    POST /api/v1/users/calculate-reward

    1. Fetch user by user_id → get loyalty_score and biogas_plant name
    2. Query biogas_plant table by name → get capacity and demand
    3. If plant not found → 404 "Plant doesn't exist"
    4. Run reward_calculator utility with all factors
    5. Return full reward breakdown
    """

    # ── Step 1: fetch user ────────────────────────────────────────────────────
    user_result = await db.execute(select(User).where(User.id == payload.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # ── Step 2: fetch plant using user's biogas_plant field ───────────────────
    plant_result = await db.execute(
        select(BiogasPlant).where(BiogasPlant.name == user.biogas_plant)
    )
    plant = plant_result.scalar_one_or_none()
    if not plant:
        raise HTTPException(
            status_code=404,
            detail=f"Plant doesn't exist: '{user.biogas_plant}' not found in biogas_plant table",
        )

    # ── Step 3: calculate reward ──────────────────────────────────────────────
    breakdown = calculate_reward(
        loyalty_score=user.loyalty_score or 0,
        demand=plant.demand,
        capacity=plant.capacity,
        current_input_kg=plant.current_input_kg or 0.0,
        garbage_weight=payload.garbage_weight,
        garbage_score=payload.garbage_score,
    )

    # ── Step 4: return full breakdown ─────────────────────────────────────────
    fill_pct = round(
        ((plant.current_input_kg or 0.0) / plant.capacity * 100)
        if plant.capacity > 0 else 0.0,
        1,
    )

    # Step 4 — update user totals (summation)
    user.rewards = (user.rewards or 0) + breakdown.final_points
    user.total_garbage_weight = (user.total_garbage_weight or 0.0) + payload.garbage_weight

    # Step 5 — create transaction
    txn = UserTransaction(
        user_id=user.id,
        biogas_plant=plant.name,
        waste_deposited=f"{payload.garbage_weight} kg",
        transaction_type="credit",
        status="successful",
        reward_points=breakdown.final_points,
    )
    db.add(txn)
    await db.flush()

    return CalculateRewardResponse(
        user_id=user.id,
        user_name=user.name,
        plant_name=plant.name,
        demand_level=plant.demand,
        plant_capacity=plant.capacity,
        fill_percentage=fill_pct,
        base_points=breakdown.base_points,
        demand_multiplier=breakdown.demand_multiplier,
        capacity_multiplier=breakdown.capacity_multiplier,
        quality_multiplier=breakdown.quality_multiplier,
        loyalty_bonus_pct=breakdown.loyalty_bonus_pct,
        final_points=breakdown.final_points,
        updated_total_rewards=user.rewards,
        updated_total_garbage_weight=user.total_garbage_weight
    )