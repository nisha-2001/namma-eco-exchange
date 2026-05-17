"""
Models matching the team's actual SQL schema exactly.
Tables: user, user_transactions, biogas_plant + reward_previews (graph history)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, String, Text, Float, Integer,
    DateTime, ForeignKey, func, ARRAY
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


# ── user ─────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "customer"

    id:           Mapped[int]      = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name:         Mapped[str]      = mapped_column(String, nullable=False)
    email:        Mapped[str]      = mapped_column(String, unique=True, index=True, nullable=False)
    phone_number: Mapped[str]      = mapped_column(String, nullable=False)
    address:      Mapped[str]      = mapped_column(String, nullable=False)
    biogas_plant: Mapped[str]      = mapped_column(String, nullable=False)   # plant name/id as string
    rewards:      Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, default=0)
    loyalty_score:Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, default=0)
    total_garbage_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    transactions:    Mapped[list["UserTransaction"]] = relationship("UserTransaction", back_populates="user")
    reward_previews: Mapped[list["RewardPreview"]]   = relationship("RewardPreview",   back_populates="user")


# ── biogas_plant ──────────────────────────────────────────────────────────────

class BiogasPlant(Base):
    __tablename__ = "biogas_plant"

    id:             Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name:           Mapped[str] = mapped_column(String, nullable=False)
    location:       Mapped[str] = mapped_column(String, nullable=False)
    capacity:       Mapped[int] = mapped_column(BigInteger, nullable=False)   # in kg
    drop_off_points: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    demand:         Mapped[str] = mapped_column(String, nullable=False)       # low/medium/high

    # Extra fields we need for dynamic pricing — not in original schema, added as nullable
    current_input_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ── user_transactions ─────────────────────────────────────────────────────────

class UserTransaction(Base):
    __tablename__ = "user_transactions"

    id:               Mapped[int]          = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id:          Mapped[int]          = mapped_column(BigInteger, ForeignKey("customer.id"), nullable=False)
    biogas_plant:     Mapped[str]          = mapped_column(String, nullable=False)
    waste_deposited:  Mapped[str]          = mapped_column(String, nullable=False)   # e.g. "10 kg"
    transaction_type: Mapped[str]          = mapped_column(String, nullable=False)   # credit/debit
    status:           Mapped[Optional[str]]= mapped_column(String, nullable=True)
    reward_points:    Mapped[Optional[int]]= mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship("User", back_populates="transactions")


# ── reward_previews (our addition — drives the pricing graph) ─────────────────
# Not in the team schema — append-only log of every Claude pricing call.
# Powers the "pts/kg through the day / last week" graph.

class RewardPreview(Base):
    __tablename__ = "reward_previews"

    id:              Mapped[int]           = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id:         Mapped[int]           = mapped_column(BigInteger, ForeignKey("customer.id"), nullable=False)
    plant_id:        Mapped[int]           = mapped_column(BigInteger, ForeignKey("biogas_plant.id"), nullable=False)

    weight_kg:       Mapped[float]         = mapped_column(Float, nullable=False)
    multiplier:      Mapped[float]         = mapped_column(Float, nullable=False)
    points_estimate: Mapped[int]           = mapped_column(Integer, nullable=False)
    plant_fill_pct:  Mapped[float]         = mapped_column(Float, nullable=False)
    user_rating:     Mapped[float]         = mapped_column(Float, nullable=False)
    demand_level:    Mapped[str]           = mapped_column(String(20), nullable=False)
    ai_reason:       Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="reward_previews")