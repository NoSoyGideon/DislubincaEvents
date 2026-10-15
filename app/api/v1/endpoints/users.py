import secrets
import string
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
import uuid

from app.api import deps
from app.core import security
from app.core.database import get_db
from app.models.user import User
from app.models.route import Route
from app.schemas.enums import UserRole
from app.schemas.user_schema import (
    UserCreate,
    UserCreateResponse,
    UserResponse,
    UserUpdate
)

router = APIRouter()

@router.get("", response_model=List[UserResponse], summary="Listar Usuarios (Solo ADMIN)")
async def get_users(
    is_active: Optional[bool] = Query(None, description="Filtrar por estado activo/inactivo"),
    role: Optional[UserRole] = Query(None, description="Filtrar por rol de usuario"),
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve la lista completa de usuarios registrados en la empresa."""
    query = select(User).options(selectinload(User.route))
    
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role is not None:
        query = query.where(User.role == role.value)
        
    result = await db.execute(query.order_by(User.name))
    users = result.scalars().all()
    return users


@router.post("", response_model=UserCreateResponse, status_code=status.HTTP_201_CREATED, summary="Crear Usuario (Solo ADMIN)")
async def create_user(
    user_in: UserCreate,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Registra un nuevo empleado en la base de datos y le genera una clave temporal aleatoria."""
    # 1. Validar que el correo no esté duplicado
    result_email = await db.execute(select(User).where(User.email == user_in.email))
    if result_email.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya se encuentra registrado"
        )
    
    # 2. Validar y obtener el ID de la ruta mediante el número de ruta enviado (ej: route=10, route=15)
    route_id_to_assign = None
    route_obj = None
    if user_in.route is not None:
        result_route = await db.execute(select(Route).where(Route.number == user_in.route))
        route_obj = result_route.scalars().first()
        
        if not route_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La ruta número {user_in.route} no existe en el sistema"
            )

        assigned_route = await db.execute(
            select(User).where(User.route_id == route_obj.id)
        )
        if assigned_route.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La ruta número {user_in.route} ya está asignada a otro usuario"
            )
        route_id_to_assign = route_obj.id
    
    # 3. Generar contraseña temporal aleatoria (ej: Dis#9a81)
    alphabet = string.ascii_letters + string.digits
    temp_password = "Dis#" + ''.join(secrets.choice(alphabet) for _ in range(4))
    
    # 4. Crear instancia de usuario
    new_user = User(
        name=user_in.name,
        email=user_in.email,
        password_hash=security.get_password_hash(temp_password),
        role=user_in.role.value,
        position=user_in.position.value if user_in.position else None,
        route_id=route_id_to_assign,
        is_active=True
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    return UserCreateResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        role=new_user.role,
        position=new_user.position,
        route=route_obj.number if route_obj else None,
        temporary_password=temp_password,
        is_active=new_user.is_active,
        created_at=new_user.created_at,
    )

@router.get("/{user_id}", response_model=UserResponse, summary="Obtener Detalle de Usuario (Solo ADMIN)")
async def get_user_by_id(
    user_id: uuid.UUID,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene la información detallada de la cuenta de un usuario específico."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.route))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    return user


@router.put("/{user_id}", response_model=UserResponse, summary="Editar Usuario (Solo ADMIN)")
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Modifica el nombre, cargo, rol o ruta asignada de un empleado."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.route))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Validar correo único si se está intentando cambiar
    if user_in.email is not None and user_in.email != user.email:
        res_email = await db.execute(select(User).where(User.email == user_in.email))
        if res_email.scalars().first():
            raise HTTPException(status_code=400, detail="El correo ingresado ya pertenece a otro usuario")
        user.email = user_in.email

    # Validar y actualizar la ruta buscando por NÚMERO DE RUTA (ej: route=15)
    if user_in.route is not None:
        res_route = await db.execute(select(Route).where(Route.number == user_in.route))
        route_obj = res_route.scalars().first()
        
        if not route_obj:
            raise HTTPException(
                status_code=404, 
                detail=f"La ruta número {user_in.route} no existe en el sistema"
            )
        user.route_id = route_obj.id

    if user_in.name is not None:
        user.name = user_in.name
    if user_in.role is not None:
        user.role = user_in.role.value
    if user_in.position is not None:
        user.position = user_in.position.value
    if user_in.is_active is not None:
        user.is_active = user_in.is_active

    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["route"])
    return user


@router.patch("/{user_id}/toggle-active", response_model=UserResponse, summary="Activar/Desactivar Usuario (Solo ADMIN)")
async def toggle_user_active(
    user_id: uuid.UUID,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Alterna el estado de un usuario entre activo e inactivo (Soft Delete)."""
    if user_id == admin_user.id:
        raise HTTPException(status_code=400, detail="No puedes desactivar tu propia cuenta de administrador")

    result = await db.execute(
        select(User)
        .options(selectinload(User.route))
        .where(User.id == user_id)
    )
    user = result.scalars().first()
    
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    user.is_active = not user.is_active
    db.add(user)
    await db.commit()
    await db.refresh(user, attribute_names=["route"])
    return user