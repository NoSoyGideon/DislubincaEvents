import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator
import uuid

# Entrada para Login
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="carlos.mendoza@dislubinca.com")
    password: str = Field(..., min_length=4, example="clave_segura_123")

# Respuesta exitosa de Login (Token JWT)
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Contenido decodificado del JWT Token
class TokenPayload(BaseModel):
    sub: Optional[str] = None

# Respuesta del perfil activo (GET /auth/me)
class UserMeResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str
    position: Optional[str] = None
    route_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True

# Entrada para cambiar clave propia
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=4)
    new_password: str = Field(..., min_length=6)

# Respuesta del Reset por Admin

class AdminResetPasswordResponse(BaseModel):
    user_id: uuid.UUID
    temporary_password: str
    message: str = "Contraseña restablecida exitosamente"
    
# 1. Solicitud de código al correo
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., example="usuario@dislubinca.com")

# 2. Verificación del código de 6 dígitos
class VerifyResetCodeRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, example="849201")

# 3. Cambio final de contraseña
class ResetPasswordRequest(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str = Field(..., min_length=6, example="NuevaClave2026#")

    @field_validator("new_password")
    @classmethod
    def validate_password_complexity(cls, value: str) -> str:
        if not re.search(r"\d", value):
            raise ValueError("La contraseña debe contener al menos un número (0-9)")
        return value