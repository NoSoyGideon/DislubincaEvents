from typing import Optional, List
from datetime import date
from pydantic import BaseModel, Field
import uuid

from app.schemas.enums import EventType, ClientClassification

# --- Insumos Asignados al Evento ---

class EventResourceItem(BaseModel):
    resource_id: uuid.UUID
    assigned_quantity: int = Field(..., gt=0, example=20)

class EventResourceDetailResponse(BaseModel):
    resource_id: uuid.UUID
    sku_code: Optional[str] = None
    name: str
    quantity: int
    unit_price_usd: float
    total_usd: float


# --- Respuestas del Feed y Dashboard ---

class EventUpcomingResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    event_type: EventType
    official_date: date
    event_date: date
    days_remaining: int
    classification: ClientClassification
    route: int
    status: str  # PENDIENTE, CONFIRMADO, REPROGRAMADO
    has_custom_resources: bool


class EventStatsResponse(BaseModel):
    total_events_month: int
    pending_assignments: int
    total_budget_usd: float
    next_event_days: Optional[int] = None


# --- Detalle y Modificaciones ---

class EventDetailResponse(BaseModel):
    id: uuid.UUID
    client_id: uuid.UUID
    client_name: str
    official_date: date
    event_date: date
    status: str
    route: int
    classification: ClientClassification
    assigned_resources: List[EventResourceDetailResponse] = []
    total_cost_usd: float


class EventRescheduleRequest(BaseModel):
    event_date: date = Field(..., example="2026-10-18")


class EventResourcesUpdateResponse(BaseModel):
    event_id: uuid.UUID
    total_resources_count: int
    total_cost_usd: float
    assigned_resources: List[EventResourceDetailResponse] = []