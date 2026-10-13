from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
import uuid

class Resource(SQLModel, table=True):
    __tablename__ = "resources"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    sku_code: Optional[str] = Field(default=None, max_length=50, index=True, nullable=True)
    name: str = Field(max_length=150, nullable=False)
    unit_price_usd: float = Field(default=0.0, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    # Relaciones
    client_base_assignments: List["ClientBaseResource"] = Relationship(back_populates="resource")
    event_assignments: List["EventResourceAssigned"] = Relationship(back_populates="resource")