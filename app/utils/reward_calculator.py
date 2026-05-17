"""
Reward calculation utility.

Factors used:
  - loyalty_score   (from user table)    — stored as int×10, e.g. 48 = 4.8 stars
  - demand          (from biogas_plant)  — "low" | "medium" | "high"
  - capacity        (from biogas_plant)  — plant capacity in kg
  - current_input_kg(from biogas_plant)  — how full the plant currently is
  - garbage_weight  (from request)       — kg of waste deposited
  - garbage_score   (from request)       — quality score 0.0–1.0 from vision AI

Formula (all multipliers stack):
  base_points      = garbage_weight × BASE_PTS_PER_KG (10)
  demand_mult      = 0.8 (low) | 1.2 (medium) | 1.8 (high)
  capacity_mult    = 1.0 + (1 − fill_pct) × 0.5
                     → rewards more when plant has room (fill_pct low = high reward)
  quality_mult     = 0.5 + garbage_score × 1.0   → range 0.5–1.5
  loyalty_bonus    = (loyalty_score / 10) × 0.05 → e.g. 4.8 stars = +24% bonus
  final_points     = base × demand_mult × capacity_mult × quality_mult × (1 + loyalty_bonus)
"""

from dataclasses import dataclass

BASE_PTS_PER_KG = 10.0

DEMAND_MULTIPLIERS = {
    "low":    0.8,
    "medium": 1.2,
    "high":   1.8,
}


@dataclass
class RewardBreakdown:
    """Full breakdown — useful for debugging and returning to the client."""
    garbage_weight:    float
    garbage_score:     float
    base_points:       float
    demand_multiplier: float
    capacity_multiplier: float
    quality_multiplier: float
    loyalty_bonus_pct: float
    final_points:      int        # rounded to nearest int


def calculate_reward(
    loyalty_score:    int,      # raw DB value, divide by 10 to get star rating
    demand:           str,      # "low" | "medium" | "high"
    capacity:         int,      # plant max capacity in kg
    current_input_kg: float,    # current waste in plant (kg)
    garbage_weight:   float,    # kg deposited — from request payload
    garbage_score:    float,    # 0.0–1.0 quality score — from request payload
) -> RewardBreakdown:
    """
    Returns a RewardBreakdown with the final_points and every factor that
    contributed to it, so callers can log or return the full breakdown.
    """
    # ── Base ─────────────────────────────────────────────────────────────────
    base = garbage_weight * BASE_PTS_PER_KG

    # ── Demand multiplier ─────────────────────────────────────────────────────
    demand_mult = DEMAND_MULTIPLIERS.get(demand.lower(), 1.0)

    # ── Capacity multiplier ───────────────────────────────────────────────────
    # Plant fill % → lower fill = more incentive to deposit
    fill_pct = (current_input_kg or 0.0) / capacity if capacity > 0 else 0.0
    fill_pct = max(0.0, min(1.0, fill_pct))   # clamp 0–1
    capacity_mult = round(1.0 + (1.0 - fill_pct) * 0.5, 4)   # range 1.0–1.5

    # ── Quality multiplier ────────────────────────────────────────────────────
    # garbage_score 0.0 → mult 0.5 | score 1.0 → mult 1.5
    score = max(0.0, min(1.0, garbage_score))
    quality_mult = round(0.5 + score * 1.0, 4)

    # ── Loyalty bonus ─────────────────────────────────────────────────────────
    # loyalty_score stored as int×10 in DB (48 = 4.8 stars)
    star_rating   = (loyalty_score or 0) / 10.0    # e.g. 4.8
    loyalty_bonus = round(star_rating * 0.05, 4)   # e.g. +24%

    # ── Final ─────────────────────────────────────────────────────────────────
    raw = base * demand_mult * capacity_mult * quality_mult * (1.0 + loyalty_bonus)
    final = max(1, round(raw))   # minimum 1 point

    return RewardBreakdown(
        garbage_weight=garbage_weight,
        garbage_score=garbage_score,
        base_points=round(base, 2),
        demand_multiplier=demand_mult,
        capacity_multiplier=capacity_mult,
        quality_multiplier=quality_mult,
        loyalty_bonus_pct=round(loyalty_bonus * 100, 2),
        final_points=final,
    )