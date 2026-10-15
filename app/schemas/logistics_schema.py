from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator
import uuid

from app.schemas.enums import ClientClassification

# --- Schemas del Catálogo de SKUs ---

class ResourceBase(BaseModel):
    sku_code: Optional[str] = Field(None, max_length=50, example="CAM-POLO")
    name: str = Field(..., max_length=150, example="Camisa Polo Tipo L")
    unit_price_usd: float = Field(..., gt=0, example=8.00, description="El precio unitario debe ser mayor a $0 USD")

    @field_validator("sku_code")
    @classmethod
    def sanitize_sku(cls, v: Optional[str]) -> Optional[str]:
        if v:
            return v.strip().upper()
        return v


class ResourceCreate(ResourceBase):
    pass


class ResourceUpdate(BaseModel):
    sku_code: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=150)
    unit_price_usd: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None


class ResourceResponse(ResourceBase):
    id: uuid.UUID
    is_active: bool

    class Config:
        from_attributes = True


# --- Schemas del Reporte Consolidado Mensual ---

class MonthlyItemSummary(BaseModel):
    resource_id: uuid.UUID
    sku_code: Optional[str] = None
    name: str
    total_quantity: int
    unit_price_usd: float
    total_usd: float


class MonthlySummaryResponse(BaseModel):
    month: int
    year: int
    total_events: int
    events_pending: int
    total_cost_usd: float
    budget_by_classification: Dict[str, float]
    items_summary: List[MonthlyItemSummary]