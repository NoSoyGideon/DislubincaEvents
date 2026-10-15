import secrets
import string
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import uuid

from app.api import deps
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.models.password_reset import PasswordResetCode
from app.schemas.auth_schema import (
    LoginRequest,
    TokenResponse,
    UserMeResponse,
    ChangePasswordRequest,
    AdminResetPasswordResponse,
    ForgotPasswordRequest,
    VerifyResetCodeRequest,
    ResetPasswordRequest
)

from app.services.email_service import send_reset_code_email

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



@router.post("/{user_id}/reset-password", response_model=AdminResetPasswordResponse, summary="Restablecer Clave (Solo ADMIN)")
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
    
# ----------------------------------------------------------------------
#  REQUEST CODE BY EMAIL
# ----------------------------------------------------------------------
@router.post("/forgot-password", summary="1. Solicitar Código de Recuperación")
async def forgot_password(
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Genera y envía un código de 6 dígitos al correo del usuario si existe."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    
    # Por seguridad, si el correo no existe respondemos con éxito genérico para evitar filtrado de usuarios
    if not user or not user.is_active:
        return {"detail": "Si el correo está registrado, recibirás un código de verificación en breve."}
    
    # Genera código numérico aleatorio de 6 dígitos (ej: "849201")
    reset_code = "".join([str(secrets.randbelow(10)) for _ in range(6)])
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    # Registra el código en PostgreSQL
    code_entry = PasswordResetCode(
        email=user.email,
        code=reset_code,
        expires_at=expires_at
    )
    db.add(code_entry)
    await db.commit()
    
    # Envía el correo transaccional
    await send_reset_code_email(email_to=user.email, code=reset_code)
    
    return {"detail": "Si el correo está registrado, recibirás un código de verificación en breve."}


# ----------------------------------------------------------------------
# 2. VERIFICAR SI EL CÓDIGO ES VÁLIDO
# ----------------------------------------------------------------------
@router.post("/verify-reset-code", summary="2. Verificar Código de 6 Dígitos")
async def verify_reset_code(
    data: VerifyResetCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Valida si el código introducido por el usuario sigue activo y no ha expirado."""
    stmt = (
        select(PasswordResetCode)
        .where(PasswordResetCode.email == data.email)
        .where(PasswordResetCode.code == data.code)
        .order_by(PasswordResetCode.created_at.desc())
    )
    result = await db.execute(stmt)
    reset_entry = result.scalars().first()
    
    if not reset_entry or not reset_entry.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código es inválido o ha expirado"
        )
        
    return {"valid": True, "detail": "Código verificado exitosamente"}


# ----------------------------------------------------------------------
# 3. CAMBIAR CONTRASEÑA CON EL CÓDIGO VERIFICADO
# ----------------------------------------------------------------------
@router.post("/reset-password", summary="3. Restablecer Contraseña Definitiva")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    """Aplica la nueva contraseña en PostgreSQL si el código de 6 dígitos es válido."""
    # 1. Valida el código
    stmt = (
        select(PasswordResetCode)
        .where(PasswordResetCode.email == data.email)
        .where(PasswordResetCode.code == data.code)
        .order_by(PasswordResetCode.created_at.desc())
    )
    result = await db.execute(stmt)
    reset_entry = result.scalars().first()
    
    if not reset_entry or not reset_entry.is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de verificación inválido o expirado"
        )
    
    # 2. Obtiene el usuario
    user_stmt = select(User).where(User.email == data.email)
    user_result = await db.execute(user_stmt)
    user = user_result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    # 3. Actualiza la clave con Bcrypt y marca el código como usado
    user.password_hash = security.get_password_hash(data.new_password)
    reset_entry.is_used = True
    
    db.add(user)
    db.add(reset_entry)
    await db.commit()
    
    return {"detail": "Contraseña actualizada exitosamente. Ya puedes iniciar sesión."}