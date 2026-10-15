from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator
import uuid

from app.schemas.enums import ClientClassification

# --- Schemas de Recursos Base del Cliente ---

class ClientBaseResourceItem(BaseModel):
    resource_id: uuid.UUID
    quantity: int = Field(default=1, gt=0)

class ClientBaseResourceResponse(ClientBaseResourceItem):
    id: uuid.UUID
    sku_code: Optional[str] = None
    name: str
    unit_price_usd: float

    class Config:
        from_attributes = True


# --- Schemas del Cliente ---

class ClientBase(BaseModel):
    rif: str = Field(..., max_length=50, example="J-12345678-9")
    id_crm: Optional[str] = Field(None, max_length=50, example="CRM-101")
    name: str = Field(..., max_length=200, example="Distribuidora Central C.A.")
    anniversary_date: date = Field(..., example="2018-10-12")
    owner_name: Optional[str] = Field(None, max_length=100)
    owner_birthdate: Optional[date] = None
    classification: ClientClassification = Field(default=ClientClassification.RESTO, example=ClientClassification.TOP_5)
    route: int = Field(..., example=10, description="Número público de la ruta")
    zone: Optional[str] = Field(None, example="centro 1")
    address: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("route", mode="before")
    @classmethod
    def route_number_from_relationship(cls, value):
        return getattr(value, "number", value)

class ClientCreate(ClientBase):
    # Asignación inicial opcional de recursos por defecto al crear
    base_resources: Optional[List[ClientBaseResourceItem]] = []

class ClientUpdate(BaseModel):
    rif: Optional[str] = Field(None, max_length=50)
    id_crm: Optional[str] = Field(None, max_length=50)
    name: Optional[str] = Field(None, max_length=200)
    anniversary_date: Optional[date] = None
    owner_name: Optional[str] = None
    owner_birthdate: Optional[date] = None
    classification: Optional[ClientClassification] = None
    route: Optional[int] = Field(None, example=15)
    zone: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None

class ClientResponse(ClientBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ClientDetailResponse(ClientResponse):
    base_resources: List[ClientBaseResourceResponse] = []

class ExcelImportResponse(BaseModel):
    created: int
    updated: int
    total_processed: int
    errors: List[str] = []