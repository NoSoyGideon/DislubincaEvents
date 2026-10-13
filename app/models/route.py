from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship

class Route(SQLModel, table=True):
    __tablename__ = "routes"

    id: Optional[int] = Field(default=None, primary_key=True)
    number: int = Field(unique=True, index=True, nullable=False)

    # Relaciones
    users: List["User"] = Relationship(back_populates="route")
    clients: List["Client"] = Relationship(back_populates="route")