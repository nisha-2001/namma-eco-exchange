from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, Field


# ── User ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    name:         str
    email:        EmailStr
    phone_number: str
    address:      str
    biogas_plant: str           # plant id as string
    loyalty_score: int = 35     # default 3.5 rating → stored as 35


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            int
    name:          str
    email:         str
    phone_number:  str
    address:       str
    biogas_plant:  str
    rewards:       Optional[int]
    loyalty_score: Optional[int]
    created_at:    datetime
    total_garbage_weight: Optional[float]


# ── Transaction ──────────────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               int
    user_id:          int
    biogas_plant:     str
    waste_deposited:  str
    transaction_type: str
    status:           Optional[str]
    reward_points:    Optional[int]
    created_at:       datetime


# ── Reward preview ───────────────────────────────────────────────────────────

class RewardPreviewRequest(BaseModel):
    weight_kg: float = Field(..., ge=0.5, description="kg of waste — minimum 0.5 kg")


class RewardPreviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:              int
    weight_kg:       float
    multiplier:      float
    points_estimate: int
    plant_fill_pct:  float
    user_rating:     float
    demand_level:    str
    ai_reason:       Optional[str]
    created_at:      datetime


# ── Graph data ───────────────────────────────────────────────────────────────

class PricingHistoryPoint(BaseModel):
    timestamp:     datetime
    multiplier:    float
    points_per_kg: float
    plant_fill_pct: float
    demand_level:  str


class PricingHistoryResponse(BaseModel):
    user_rating:           float
    history:               list[PricingHistoryPoint]
    current_multiplier:    float
    current_points_per_kg: float


# ── Waste Classification ───────────────────────────────────────────────────

class ImageRequest(BaseModel):
    image_base64: str


class MultiImageRequest(BaseModel):
    images: list[str]


class WasteClassificationResponse(BaseModel):
    classification: str  # "organic" or "inorganic"
    confidence: float    # Confidence score of the classification


class WasteClassificationBatchResponse(BaseModel):
    results: list[WasteClassificationResponse]
    waste_ratio: float  # Ratio of organic waste to total images
    garbageRating: float  # Ratio of organic waste images to total images sent


# ── Groq API Key ─────────────────────────────────────────────────────────────

class GroqAPIKeyRequest(BaseModel):
    groq_api_key: str

    class Config:
        extra = "forbid"


# ── Reward calculation ────────────────────────────────────────────────────────

class CalculateRewardRequest(BaseModel):
    user_id:        int   = Field(..., description="ID of the user depositing waste")
    garbage_weight: float = Field(..., gt=0, description="Weight of waste in kg")
    garbage_score:  float = Field(..., ge=0.0, le=1.0, description="Quality score from vision AI (0.0–1.0)")


class CalculateRewardResponse(BaseModel):
    # User & plant context
    user_id:        int
    user_name:      str
    plant_name:     str
    demand_level:   str
    plant_capacity: int
    fill_percentage: float

    # Reward breakdown
    base_points:          float
    demand_multiplier:    float
    capacity_multiplier:  float
    quality_multiplier:   float
    loyalty_bonus_pct:    float
    final_points:         int
    updated_total_rewards: int
    updated_total_garbage_weight: float