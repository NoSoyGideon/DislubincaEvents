from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import uuid

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.resource import Resource
from app.schemas.enums import ClientClassification
from app.schemas.logistics_schema import (
    ResourceCreate,
    ResourceUpdate,
    ResourceResponse,
    MonthlySummaryResponse
)
from app.services.logistics_service import build_monthly_summary_report

router = APIRouter()

@router.get("/monthly-summary", response_model=MonthlySummaryResponse, summary="Reporte Consolidado Mensual de Compras")
async def get_monthly_summary(
    month: int = Query(..., ge=1, le=12, description="Mes a consultar (1-12)"),
    year: int = Query(default=date.today().year, description="Año a consultar"),
    route: Optional[int] = Query(None, description="Filtrar por número de ruta"),
    classification: Optional[ClientClassification] = Query(None, description="Filtrar por clasificación"),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Consolida la lista de insumos/SKUs y presupuesto total ($) requeridos para el mes de compras."""
    class_val = classification.value if classification else None
    return await build_monthly_summary_report(
        db=db,
        month=month,
        year=year,
        route_number=route,
        classification=class_val
    )


@router.get("/resources", response_model=List[ResourceResponse], summary="Listar Catálogo de SKUs")
async def get_resources(
    is_active: bool = Query(True, description="Mostrar activos o inactivos"),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve la lista completa de productos/obsequios del catálogo."""
    query = select(Resource).where(Resource.is_active == is_active).order_by(Resource.name)
    result = await db.execute(query)
    resources = result.scalars().all()
    return resources


@router.post("/resources", response_model=ResourceResponse, status_code=status.HTTP_201_CREATED, summary="Agregar Producto al Catálogo (Solo ADMIN)")
async def create_resource(
    resource_in: ResourceCreate,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Registra un nuevo ítem/regalo en el catálogo general."""
    if resource_in.sku_code:
        res_sku = await db.execute(select(Resource).where(Resource.sku_code == resource_in.sku_code))
        if res_sku.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El código SKU '{resource_in.sku_code}' ya existe en el catálogo"
            )

    new_resource = Resource(
        sku_code=resource_in.sku_code,
        name=resource_in.name,
        unit_price_usd=resource_in.unit_price_usd,
        is_active=True
    )
    db.add(new_resource)
    await db.commit()
    await db.refresh(new_resource)
    return new_resource


@router.put("/resources/{id}", response_model=ResourceResponse, summary="Editar Producto del Catálogo (Solo ADMIN)")
async def update_resource(
    id: uuid.UUID,
    resource_in: ResourceUpdate,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Edita el nombre, código SKU o costo en USD de un recurso."""
    result = await db.execute(select(Resource).where(Resource.id == id))
    resource = result.scalars().first()

    if not resource:
        raise HTTPException(status_code=404, detail="Recurso no encontrado en el catálogo")

    if resource_in.sku_code and resource_in.sku_code != resource.sku_code:
        res_sku = await db.execute(select(Resource).where(Resource.sku_code == resource_in.sku_code))
        if res_sku.scalars().first():
            raise HTTPException(status_code=400, detail="El código SKU ingresado pertenece a otro recurso")
        resource.sku_code = resource_in.sku_code

    if resource_in.name is not None:
        resource.name = resource_in.name
    if resource_in.unit_price_usd is not None:
        resource.unit_price_usd = resource_in.unit_price_usd
    if resource_in.is_active is not None:
        resource.is_active = resource_in.is_active

    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


@router.patch("/resources/{id}/toggle-active", response_model=ResourceResponse, summary="Activar/Desactivar Producto (Solo ADMIN)")
async def toggle_resource_active(
    id: uuid.UUID,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Activa o deshabilita un SKU para que no aparezca en nuevas asignaciones."""
    result = await db.execute(select(Resource).where(Resource.id == id))
    resource = result.scalars().first()

    if not resource:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")

    resource.is_active = not resource.is_active
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource