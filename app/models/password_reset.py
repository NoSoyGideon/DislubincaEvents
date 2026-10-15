from typing import Optional
from datetime import datetime, timedelta
from sqlmodel import SQLModel, Field
import uuid

class PasswordResetCode(SQLModel, table=True):
    __tablename__ = "password_reset_codes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(index=True, nullable=False)
    code: str = Field(max_length=6, nullable=False)  # Código de 6 dígitos (ej: 849201)
    expires_at: datetime = Field(nullable=False)
    is_used: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)

    @property
    def is_valid(self) -> bool:
        """Verifica que el código no haya expirado ni haya sido utilizado."""
        return not self.is_used and datetime.utcnow() < self.expires_at