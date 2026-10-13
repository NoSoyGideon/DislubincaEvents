from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field
import uuid

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False)
    event_id: Optional[uuid.UUID] = Field(default=None, foreign_key="events.id", nullable=True)
    title: str = Field(max_length=100, nullable=False)
    message: str = Field(nullable=False)
    is_read: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True, nullable=False)