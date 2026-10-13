from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
import uuid

class SystemLog(SQLModel, table=True):
    __tablename__ = "system_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", nullable=True)
    action: str = Field(max_length=80, index=True, nullable=False)
    details: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True, nullable=False)