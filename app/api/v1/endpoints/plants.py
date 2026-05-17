from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.database import get_db
from app.models.models import BiogasPlant
from pydantic import BaseModel
from typing import Optional


router = APIRouter(prefix="/plants", tags=["Plants"])


class PlantCreate(BaseModel):
    name: str
    address: str
    daily_capacity_kg: float
    current_input_kg: float = 0.0
    demand_level: str = "medium"
    cylinders_in_stock: int = 0


class DropOffCreate(BaseModel):
    name: str
    address: str
    plant_id: uuid.UUID


class DropOffResponse(BaseModel):
    id: uuid.UUID
    name: str
    address: str
    plant_id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True


@router.patch("/{plant_id}/fill")
async def update_plant_fill(
    plant_id: uuid.UUID,
    current_input_kg: float,
    demand_level: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Admin endpoint to update plant fill level — drives the dynamic pricing."""
    result = await db.execute(select(BiogasPlant).where(BiogasPlant.id == plant_id))
    plant = result.scalar_one_or_none()
    if not plant:
        raise HTTPException(404, "Plant not found")
    plant.current_input_kg = current_input_kg
    if demand_level:
        plant.demand_level = demand_level
    await db.flush()
    return {"ok": True, "fill_pct": round(current_input_kg / plant.daily_capacity_kg * 100, 1)}

@router.get("/{plant_id}/drop-off-points")
async def get_drop_off_points(plant_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BiogasPlant).where(BiogasPlant.id == plant_id))
    plant = result.scalar_one_or_none()
    if not plant:
        raise HTTPException(404, "Plant not found")
    return {
        "plant_id": plant_id,
        "plant_name": plant.name,
        "drop_off_points": plant.drop_off_points
    }