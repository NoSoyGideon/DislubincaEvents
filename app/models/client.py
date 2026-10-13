from typing import Optional, List
from datetime import date, datetime
from sqlmodel import SQLModel, Field, Relationship
import uuid

class ClientBaseResource(SQLModel, table=True):
    __tablename__ = "client_base_resources"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", nullable=False)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", nullable=False)
    quantity: int = Field(default=1, nullable=False)

    # Relaciones
    client: "Client" = Relationship(back_populates="base_resources")
    resource: "Resource" = Relationship(back_populates="client_base_assignments")


class Client(SQLModel, table=True):
    __tablename__ = "clients"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    rif: str = Field(max_length=50, unique=True, index=True, nullable=False)
    id_crm: Optional[str] = Field(default=None, max_length=50, index=True, nullable=True)
    name: str = Field(max_length=200, index=True, nullable=False)
    
    anniversary_date: date = Field(index=True, nullable=False)
    owner_name: Optional[str] = Field(default=None, max_length=100, nullable=True)
    owner_birthdate: Optional[date] = Field(default=None, index=True, nullable=True)
    
    classification: str = Field(default="RESTO", max_length=20, nullable=False) # TOP 5, TOP 2, RESTO
    route_id: int = Field(foreign_key="routes.id", nullable=False)
    zone: Optional[str] = Field(default=None, max_length=50, nullable=True) # centro 1, sur 1, norte 1, machiques
    address: Optional[str] = Field(default=None, nullable=True)
    phone: Optional[str] = Field(default=None, max_length=50, nullable=True)
    
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relaciones
    route: "Route" = Relationship(back_populates="clients")
    base_resources: List["ClientBaseResource"] = Relationship(back_populates="client")
    events: List["Event"] = Relationship(back_populates="client")