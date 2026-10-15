from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, or_, extract
import uuid
from sqlalchemy.orm import selectinload

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.client import Client, ClientBaseResource
from app.models.route import Route
from app.models.resource import Resource
from app.schemas.enums import ClientClassification
from app.schemas.client_schema import (
    ClientCreate,
    ClientUpdate,
    ClientResponse,
    ClientDetailResponse,
    ExcelImportResponse
)
from app.services.excel_service import process_excel_import_stub

router = APIRouter()

@router.get("", response_model=List[ClientResponse], summary="Listar Clientes con Búsqueda y Filtros")
async def get_clients(
    search: Optional[str] = Query(None, description="Búsqueda por Nombre, RIF o Código CRM"),
    route: Optional[int] = Query(None, description="Filtrar por número de ruta (ej: 10, 15)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Mes de aniversario (1-12)"),
    classification: Optional[ClientClassification] = Query(None, description="Filtrar por clasificación"),
    is_active: bool = Query(True, description="Mostrar activos/inactivos"),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Consulta el directorio general de clientes con filtros combinables."""
    query = select(Client).options(selectinload(Client.route)).where(Client.is_active == is_active)

    # 1. Filtro de búsqueda general
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Client.name.ilike(search_pattern),
                Client.rif.ilike(search_pattern),
                Client.id_crm.ilike(search_pattern)
            )
        )

    # 2. Filtro por número de ruta
    if route is not None:
        res_route = await db.execute(select(Route).where(Route.number == route))
        route_obj = res_route.scalars().first()
        if route_obj:
            query = query.where(Client.route_id == route_obj.id)
        else:
            return []  # Si la ruta buscada no existe, retorna lista vacía

    # 3. Filtro por mes de aniversario
    if month is not None:
        query = query.where(extract('month', Client.anniversary_date) == month)

    # 4. Filtro por clasificación
    if classification is not None:
        query = query.where(Client.classification == classification.value)

    result = await db.execute(query.order_by(Client.name))
    clients = result.scalars().all()
    return clients


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED, summary="Registrar Cliente Manualmente (Solo ADMIN)")
async def create_client(
    client_in: ClientCreate,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Registra manualmente un nuevo cliente verificando la unicidad del RIF y del Código CRM."""
    
    # 1. Validar RIF único
    res_rif = await db.execute(select(Client).where(Client.rif == client_in.rif))
    if res_rif.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El RIF ingresado ya pertenece a otro cliente"
        )

    # 2. Validar ID CRM único si fue proporcionado
    if client_in.id_crm:
        res_crm = await db.execute(select(Client).where(Client.id_crm == client_in.id_crm))
        if res_crm.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El Código CRM ingresado ya se encuentra registrado"
            )

    # 3. Validar existencia de la ruta mediante su número
    res_route = await db.execute(select(Route).where(Route.number == client_in.route))
    route_obj = res_route.scalars().first()
    if not route_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La ruta número {client_in.route} no existe"
        )

    # 4. Crear cliente
    new_client = Client(
        rif=client_in.rif,
        id_crm=client_in.id_crm,
        name=client_in.name,
        anniversary_date=client_in.anniversary_date,
        owner_name=client_in.owner_name,
        owner_birthdate=client_in.owner_birthdate,
        classification=client_in.classification.value,
        route_id=route_obj.id,
        zone=client_in.zone,
        address=client_in.address,
        phone=client_in.phone,
        is_active=True
    )
    db.add(new_client)
    await db.commit()
    await db.refresh(new_client, attribute_names=["route"])

    # 5. Registrar asignaciones base de recursos si se especificaron
    if client_in.base_resources:
        for item in client_in.base_resources:
            base_res = ClientBaseResource(
                client_id=new_client.id,
                resource_id=item.resource_id,
                quantity=item.quantity
            )
            db.add(base_res)
        await db.commit()

    await db.refresh(new_client, attribute_names=["route"])

    return new_client


@router.get("/{client_id}", response_model=ClientDetailResponse, summary="Obtener Detalle del Cliente")
async def get_client_by_id(
    client_id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve la ficha completa del cliente incluyendo sus insumos base asignados."""
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.route))
        .where(Client.id == client_id)
    )
    client = result.scalars().first()

    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Cargar recursos base asociados
    res_base = await db.execute(
        select(ClientBaseResource, Resource)
        .join(Resource, ClientBaseResource.resource_id == Resource.id)
        .where(ClientBaseResource.client_id == client_id)
    )
    base_resources_list = []
    for base_res, resource in res_base.all():
        base_resources_list.append({
            "id": base_res.id,
            "resource_id": resource.id,
            "sku_code": resource.sku_code,
            "name": resource.name,
            "unit_price_usd": resource.unit_price_usd,
            "quantity": base_res.quantity
        })

    response_data = ClientDetailResponse.model_validate(client)
    response_data.base_resources = base_resources_list
    return response_data


@router.put("/{client_id}", response_model=ClientResponse, summary="Editar Cliente (Solo ADMIN)")
async def update_client(
    client_id: uuid.UUID,
    client_in: ClientUpdate,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Modifica los datos generales o la ruta asignada a un cliente."""
    result = await db.execute(
        select(Client)
        .options(selectinload(Client.route))
        .where(Client.id == client_id)
    )
    client = result.scalars().first()

    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    # Validaciones de duplicados
    if client_in.rif is not None and client_in.rif != client.rif:
        res_rif = await db.execute(select(Client).where(Client.rif == client_in.rif))
        if res_rif.scalars().first():
            raise HTTPException(status_code=400, detail="El RIF ingresado pertenece a otro cliente")
        client.rif = client_in.rif

    if client_in.id_crm is not None and client_in.id_crm != client.id_crm:
        res_crm = await db.execute(select(Client).where(Client.id_crm == client_in.id_crm))
        if res_crm.scalars().first():
            raise HTTPException(status_code=400, detail="El Código CRM pertenece a otro cliente")
        client.id_crm = client_in.id_crm

    if client_in.route is not None:
        res_route = await db.execute(select(Route).where(Route.number == client_in.route))
        route_obj = res_route.scalars().first()
        if not route_obj:
            raise HTTPException(status_code=404, detail="La ruta especificada no existe")
        client.route_id = route_obj.id

    if client_in.name is not None:
        client.name = client_in.name
    if client_in.anniversary_date is not None:
        client.anniversary_date = client_in.anniversary_date
    if client_in.owner_name is not None:
        client.owner_name = client_in.owner_name
    if client_in.owner_birthdate is not None:
        client.owner_birthdate = client_in.owner_birthdate
    if client_in.classification is not None:
        client.classification = client_in.classification.value
    if client_in.zone is not None:
        client.zone = client_in.zone
    if client_in.address is not None:
        client.address = client_in.address
    if client_in.phone is not None:
        client.phone = client_in.phone
    if client_in.is_active is not None:
        client.is_active = client_in.is_active

    db.add(client)
    await db.commit()
    await db.refresh(client, attribute_names=["route"])
    return client


@router.post("/import-excel", response_model=ExcelImportResponse, summary="Carga Masiva por Excel (Solo ADMIN)")
async def import_excel(
    file: UploadFile = File(...),
    admin_user: User = Depends(deps.get_current_admin_user)
):
    """Carga masiva de clientes desde un archivo Excel (Stub temporal)."""
    return await process_excel_import_stub(file)