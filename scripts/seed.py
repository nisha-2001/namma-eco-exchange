"""
python scripts/seed.py

Seeds the database with:
  - 1 biogas plant (Bellandur Bio-Energy)
  - 3 drop-off points
  - 2 users with different ratings
  - 7 days × 24 hours of pricing history (simulates plant fill rising through the day)

This makes the graph look real on demo day without needing live traffic.
"""
import asyncio
import uuid
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.models.models import Base, User, BiogasPlant, UserTransaction, RewardPreview
from app.services.claude_pricing import _fallback_multiplier  # use formula for seeding, no API calls

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://lakshmi.motagi@localhost:5432/namma-eco-2")

engine = create_async_engine(DATABASE_URL, echo=False)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as db:
        # ── Plant ────────────────────────────────────────────────────────────
        plant = BiogasPlant(
            name="Bellandur Bio-Energy",
            location="Bellandur, Bengaluru - 560103",
            capacity=5000,
            drop_off_points=["Bellandur Lake Gate", "Sarjapur Circle", "HSR Layout Sector 2"],
            demand="medium",
            current_input_kg=2100.0,
        )
        db.add(plant)
        await db.flush()   # get plant.id

        # ── Users ────────────────────────────────────────────────────────────
        user_high = User(
            name="Priya Sharma",
            email="priya@example.com",
            phone_number="9876543210",
            address="HSR Layout, Bengaluru",
            biogas_plant=str(plant.id),
            rewards=640,
            loyalty_score=48,   # maps to rating 4.8
        )
        user_low = User(
            name="Ravi Kumar",
            email="ravi@example.com",
            phone_number="9876500000",
            address="Bellandur, Bengaluru",
            biogas_plant=str(plant.id),
            rewards=120,
            loyalty_score=29,   # maps to rating 2.9
        )
        db.add(user_high)
        db.add(user_low)
        await db.flush()   # get user IDs

        # ── 7 days of pricing history ────────────────────────────────────────
        now = datetime.now(timezone.utc)

        for day_offset in range(7, 0, -1):
            day = now - timedelta(days=day_offset)
            weekday = day.weekday()
            demand = "high" if weekday < 5 else "medium"

            for hour in range(0, 24, 1):
                fill_pct = 20 + 65 * max(0, 1 - ((hour - 16) ** 2) / 128)
                fill_pct = round(min(95, fill_pct) + random.uniform(-3, 3), 1)
                ts = day.replace(hour=hour, minute=random.randint(0, 59), second=0, microsecond=0)

                for user, rating in [(user_high, 4.8), (user_low, 2.9)]:
                    ai  = _fallback_multiplier(fill_pct, demand, rating)
                    m   = ai["multiplier"]
                    pts = round(10 * 10 * m)

                    db.add(RewardPreview(
                        user_id=user.id,
                        plant_id=plant.id,
                        weight_kg=10.0,
                        multiplier=m,
                        points_estimate=pts,
                        plant_fill_pct=fill_pct,
                        user_rating=rating,
                        demand_level=demand,
                        ai_reason=ai["reason"],
                        created_at=ts,
                    ))

        await db.commit()
        print("✅ Seed complete")
        print(f"   Plant ID    : {plant.id}")
        print(f"   User (high) : {user_high.id}  — Priya, rating=4.8")
        print(f"   User (low)  : {user_low.id}   — Ravi,  rating=2.9")
        print()
        print("Try:")
        print(f"   GET /api/v1/rewards/{user_high.id}/history?days=7")
        print(f"   GET /api/v1/rewards/{user_low.id}/history?days=7")


asyncio.run(seed())