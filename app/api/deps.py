from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core import security
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth_schema import TokenPayload

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2)
) -> User:
    """Extrae el token JWT, lo valida y devuelve el objeto Usuario activo de PostgreSQL."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se pudieron validar las credenciales de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == token_data.sub))
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Usuario inactivo en el sistema")
        
    return user

def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Valida que el usuario autenticado tenga Rol ADMIN."""
    if current_user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilegios insuficientes. Se requiere Rol Administrador."
        )
    return current_user