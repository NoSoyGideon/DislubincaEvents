from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
import uuid



class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=80, nullable=False)
    email: str = Field(max_length=150, unique=True, index=True, nullable=False)
    password_hash: str = Field(max_length=255, nullable=False)
    role: str = Field(default="OPERATIVO", max_length=20, nullable=False)  # ADMIN / OPERATIVO
    position: Optional[str] = Field(default=None, max_length=100) # vendedor, supervisor, gerente, contador
    
    route_id: Optional[int] = Field(default=None, foreign_key="routes.id", nullable=True)
    google_refresh_token: Optional[str] = Field(default=None, nullable=True)
    google_calendar_id: Optional[str] = Field(default=None, max_length=255, nullable=True)
    
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    # Relaciones
    route: Optional["Route"] = Relationship(back_populates="users")