import secrets
import string
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import uuid

from app.api import deps
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth_schema import (
    LoginRequest,
    TokenResponse,
    UserMeResponse,
    ChangePasswordRequest,
    AdminResetPasswordResponse
)

router = APIRouter()

@router.post("/login", response_model=TokenResponse, summary="Iniciar Sesión")
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Autentica al usuario con correo y contraseña, devolviendo un Token JWT."""
    result = await db.execute(select(User).where(User.email == login_data.email))
    user = result.scalars().first()
    
    if not user or not security.verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cuenta de usuario inactiva",
        )
        
    access_token = security.create_access_token(subject=user.id)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserMeResponse, summary="Obtener Perfil Activo")
async def get_me(
    current_user: User = Depends(deps.get_current_user)
):
    """Devuelve la información de la cuenta activa del token enviado."""
    return current_user


@router.patch("/change-password", summary="Cambiar Contraseña Propia")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Permite al usuario logueado cambiar su clave requiriendo la clave actual."""
    if not security.verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual ingresada es incorrecta"
        )
        
    current_user.password_hash = security.get_password_hash(data.new_password)
    db.add(current_user)
    await db.commit()
    
    return {"detail": "Contraseña actualizada exitosamente"}


@router.post("/users/{user_id}/reset-password", response_model=AdminResetPasswordResponse, summary="Restablecer Clave (Solo ADMIN)")
async def reset_password_by_admin(
    user_id: uuid.UUID,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Permite al Administrador restablecer la clave de cualquier usuario generando una clave temporal."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # Genera clave temporal aleatoria de 8 caracteres (Ej: Dis#8a21)
    alphabet = string.ascii_letters + string.digits
    temp_pass = "Dis#" + ''.join(secrets.choice(alphabet) for _ in range(5))
    
    user.password_hash = security.get_password_hash(temp_pass)
    db.add(user)
    await db.commit()
    
    return {
        "user_id": user.id,
        "temporary_password": temp_pass,
        "message": f"Contraseña restablecida exitosamente para {user.name}"
    }