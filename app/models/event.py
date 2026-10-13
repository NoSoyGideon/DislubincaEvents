from typing import Optional, List
from datetime import date
from sqlmodel import SQLModel, Field, Relationship
import uuid

class EventResourceAssigned(SQLModel, table=True):
    __tablename__ = "event_resource_assigned"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    event_id: uuid.UUID = Field(foreign_key="events.id", nullable=False)
    resource_id: uuid.UUID = Field(foreign_key="resources.id", nullable=False)
    assigned_quantity: int = Field(nullable=False)

    # Relaciones
    event: "Event" = Relationship(back_populates="assigned_resources")
    resource: "Resource" = Relationship(back_populates="event_assignments")


class Event(SQLModel, table=True):
    __tablename__ = "events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    client_id: uuid.UUID = Field(foreign_key="clients.id", index=True, nullable=False)
    event_type: str = Field(default="ANIVERSARIO", max_length=30, nullable=False) # ANIVERSARIO, CUMPLEANOS_DUENO
    year: int = Field(index=True, nullable=False)
    event_date: date = Field(index=True, nullable=False)
    status: str = Field(default="PENDIENTE", max_length=20, nullable=False) # PENDIENTE, CONFIRMADO, ENTREGADO

    # Relaciones
    client: "Client" = Relationship(back_populates="events")
    assigned_resources: List["EventResourceAssigned"] = Relationship(back_populates="event")