from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid

from app.schemas.enums import UserRole, UserPosition

# 1. Base compartida
class UserBase(BaseModel):
    name: str = Field(..., max_length=80, example="Carlos Mendoza")
    email: EmailStr = Field(..., example="carlos.mendoza@dislubinca.com")
    role: UserRole = Field(default=UserRole.OPERATIVO, example=UserRole.OPERATIVO)
    position: Optional[UserPosition] = Field(default=None, example=UserPosition.VENDEDOR)
    route: Optional[int] = Field(default=None, example=10)

    @field_validator("route", mode="before")
    @classmethod
    def route_number_from_relationship(cls, value):
        return getattr(value, "number", value)

# 2. Entrada para CREAR (POST /users)
class UserCreate(UserBase):
    pass

# 3. Respuesta al CREAR (Incluye la clave temporal inicial)
class UserCreateResponse(UserBase):
    id: uuid.UUID
    temporary_password: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# 4. Entrada para EDITAR (PUT /users/{id})
class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=80)
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    position: Optional[UserPosition] = None
    route: Optional[int] = None
    is_active: Optional[bool] = None

# 5. Respuesta para LISTAR / OBTENER (GET /users)
class UserResponse(UserBase):
    id: uuid.UUID
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True