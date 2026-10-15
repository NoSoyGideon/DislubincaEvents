from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, extract
import uuid

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.client import Client, ClientBaseResource
from app.models.event import Event, EventResourceAssigned
from app.models.route import Route
from app.models.resource import Resource
from app.schemas.enums import EventType, ClientClassification
from app.schemas.enums import UserRole
from app.schemas.event_schema import (
    EventUpcomingResponse,
    EventStatsResponse,
    EventDetailResponse,
    EventRescheduleRequest,
    EventResourceItem,
    EventResourcesUpdateResponse,
    EventResourceDetailResponse
)
from app.services.event_service import calculate_days_remaining,resolve_next_event_date

router = APIRouter()

@router.get("/upcoming", response_model=List[EventUpcomingResponse], summary="Feed de Eventos Próximos (Home)")
async def get_upcoming_events(
    range_type: Optional[str] = Query("month", alias="range", description="Rango temporal: 7days, month, year"),
    include_past_days: int = Query(15, ge=0, description="Días pasados a incluir en la carga"),
    route: Optional[int] = Query(None, description="Filtrar por número de ruta"),
    event_type: Optional[EventType] = Query(None, description="Filtrar por tipo de evento"),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Devuelve el listado de eventos ordenados por fecha cercana, procesando instancias físicas y virtuales."""
    today = date.today()
    query_clients = select(Client).where(Client.is_active == True)

    if route is not None:
        res_route = await db.execute(select(Route).where(Route.number == route))
        route_obj = res_route.scalars().first()
        if route_obj:
            query_clients = query_clients.where(Client.route_id == route_obj.id)
        else:
            return []

    res_clients = await db.execute(query_clients)
    clients = res_clients.scalars().all()

    upcoming_list = []

    for client in clients:
        # Array de eventos a evaluar por cliente (Aniversario y Cumpleaños de Dueño)
        events_to_eval = [
            ("ANIVERSARIO", client.anniversary_date, EventType.ANIVERSARIO)
        ]
        if client.owner_birthdate:
            events_to_eval.append(("CUMPLEANOS_DUENO", client.owner_birthdate, EventType.CUMPLEANOS_DUENO))

        for event_key, orig_date, enum_type in events_to_eval:
            # Si el filtro por event_type está activo y no coincide, omitir
            if event_type and enum_type != event_type:
                continue

            # (2) y (3) Resolver año correcto según la fecha actual
            official_date, days_rem = resolve_next_event_date(
                            orig_date=orig_date, 
                            ref_date=today, 
                            include_past_days=include_past_days
                        )
            effective_year = official_date.year

            # Buscar si existe excepción en BD para este año
            res_event = await db.execute(
                select(Event).where(
                    Event.client_id == client.id,
                    Event.year == effective_year,
                    Event.event_type == enum_type.value
                )
            )
            event_obj = res_event.scalars().first()

            effective_date = event_obj.event_date if event_obj else official_date
            
            # Si la fecha ya pasó este año y estamos evaluando el feed hacia el futuro
            # ajustar al siguiente año si la diferencia es mayor a los días pasados permitidos
            days_rem = calculate_days_remaining(effective_date, today)
            if days_rem < -include_past_days:
                effective_year += 1
                official_date = date(effective_year, orig_date.month, orig_date.day)
                days_rem = calculate_days_remaining(official_date, today)

            # Obtener número de ruta del cliente
            res_r_num = await db.execute(select(Route).where(Route.id == client.route_id))
            r_num_obj = res_r_num.scalars().first()
            route_number = r_num_obj.number if r_num_obj else 0

            event_status = event_obj.status if event_obj else "PENDIENTE"
            has_custom = True if (event_obj and event_obj.status != "PENDIENTE") else False
            event_id = event_obj.id if event_obj else client.id

            upcoming_list.append(
                EventUpcomingResponse(
                    id=event_id,
                    client_id=client.id,
                    client_name=f"{client.name} ({'Aniversario' if enum_type == EventType.ANIVERSARIO else 'Cumpleaños ' + (client.owner_name or 'Dueño')})",
                    event_type=enum_type,
                    official_date=official_date,
                    event_date=effective_date,
                    days_remaining=days_rem,
                    classification=ClientClassification(client.classification),
                    route=route_number,
                    status=event_status,
                    has_custom_resources=has_custom
                )
            )

    # Ordenar por cercanía de días
    upcoming_list.sort(key=lambda x: x.days_remaining)
    return upcoming_list


@router.get("/stats", response_model=EventStatsResponse, summary="Métricas del Dashboard (KPIs)")
async def get_event_stats(
    month: Optional[int] = Query(None, ge=1, le=12, description="Mes a consultar (1-12)"),
    year: Optional[int] = Query(None, description="Año a consultar"),
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Calcula las métricas globales para las tarjetas del Home (Eventos del mes, pendientes y presupuesto en USD)."""
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year

    # Consultar clientes con aniversario en el mes seleccionado
    res_clients = await db.execute(
        select(Client).where(
            Client.is_active == True,
            extract('month', Client.anniversary_date) == target_month
        )
    )
    clients_in_month = res_clients.scalars().all()

    total_events = len(clients_in_month)
    pending_count = 0
    total_budget = 0.0
    next_days: Optional[int] = None

    for client in clients_in_month:
        res_event = await db.execute(
            select(Event).where(
                Event.client_id == client.id,
                Event.year == target_year
            )
        )
        event_obj = res_event.scalars().first()

        if not event_obj or event_obj.status == "PENDIENTE":
            pending_count += 1
            # Cargar recursos base por defecto
            res_base = await db.execute(
                select(ClientBaseResource, Resource)
                .join(Resource, ClientBaseResource.resource_id == Resource.id)
                .where(ClientBaseResource.client_id == client.id)
            )
            for b_res, resource in res_base.all():
                total_budget += b_res.quantity * resource.unit_price_usd
        else:
            # Cargar recursos personalizados asignados al evento
            res_assigned = await db.execute(
                select(EventResourceAssigned, Resource)
                .join(Resource, EventResourceAssigned.resource_id == Resource.id)
                .where(EventResourceAssigned.event_id == event_obj.id)
            )
            for a_res, resource in res_assigned.all():
                total_budget += a_res.assigned_quantity * resource.unit_price_usd

        # Calcular días del próximo evento
        official_date = date(target_year, client.anniversary_date.month, client.anniversary_date.day)
        eff_date = event_obj.event_date if event_obj else official_date
        d_rem = calculate_days_remaining(eff_date, today)
        if d_rem >= 0:
            if next_days is None or d_rem < next_days:
                next_days = d_rem

    return EventStatsResponse(
        total_events_month=total_events,
        pending_assignments=pending_count,
        total_budget_usd=round(total_budget, 2),
        next_event_days=next_days
    )


@router.get("/{id}", response_model=EventDetailResponse, summary="Obtener Detalle del Evento")
async def get_event_detail(
    id: uuid.UUID,
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtiene la ficha completa de una celebración y sus insumos asignados."""
    today = date.today()
    
    # Buscar primero como evento físico
    res_event = await db.execute(select(Event).where(Event.id == id))
    event_obj = res_event.scalars().first()

    if event_obj:
        client_id = event_obj.client_id
    else:
        # Si el ID recibido es el del cliente (evento virtual aún no guardado)
        client_id = id

    res_client = await db.execute(select(Client).where(Client.id == client_id))
    client = res_client.scalars().first()

    if not client:
        raise HTTPException(status_code=404, detail="Evento o cliente no encontrado")

    res_route = await db.execute(select(Route).where(Route.id == client.route_id))
    route_obj = res_route.scalars().first()
    route_number = route_obj.number if route_obj else 0

    official_date = date(today.year, client.anniversary_date.month, client.anniversary_date.day)
    eff_date = event_obj.event_date if event_obj else official_date
    event_status = event_obj.status if event_obj else "PENDIENTE"

    assigned_list: List[EventResourceDetailResponse] = []
    total_cost = 0.0

    if event_obj and event_obj.status != "PENDIENTE":
        res_assigned = await db.execute(
            select(EventResourceAssigned, Resource)
            .join(Resource, EventResourceAssigned.resource_id == Resource.id)
            .where(EventResourceAssigned.event_id == event_obj.id)
        )
        for a_res, resource in res_assigned.all():
            subtotal = a_res.assigned_quantity * resource.unit_price_usd
            total_cost += subtotal
            assigned_list.append(
                EventResourceDetailResponse(
                    resource_id=resource.id,
                    sku_code=resource.sku_code,
                    name=resource.name,
                    quantity=a_res.assigned_quantity,
                    unit_price_usd=resource.unit_price_usd,
                    total_usd=round(subtotal, 2)
                )
            )
    else:
        # Cargar de la plantilla base del cliente
        res_base = await db.execute(
            select(ClientBaseResource, Resource)
            .join(Resource, ClientBaseResource.resource_id == Resource.id)
            .where(ClientBaseResource.client_id == client.id)
        )
        for b_res, resource in res_base.all():
            subtotal = b_res.quantity * resource.unit_price_usd
            total_cost += subtotal
            assigned_list.append(
                EventResourceDetailResponse(
                    resource_id=resource.id,
                    sku_code=resource.sku_code,
                    name=resource.name,
                    quantity=b_res.quantity,
                    unit_price_usd=resource.unit_price_usd,
                    total_usd=round(subtotal, 2)
                )
            )

    event_id = event_obj.id if event_obj else client.id

    return EventDetailResponse(
        id=event_id,
        client_id=client.id,
        client_name=client.name,
        official_date=official_date,
        event_date=eff_date,
        status=event_status,
        route=route_number,
        classification=ClientClassification(client.classification),
        assigned_resources=assigned_list,
        total_cost_usd=round(total_cost, 2)
    )


@router.patch("/{id}/reschedule", response_model=EventDetailResponse, summary="Reprogramar Fecha del Evento (Solo ADMIN)")
async def reschedule_event(
    id: uuid.UUID,
    data: EventRescheduleRequest,
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Reprograma la fecha de celebración si es distinta a la oficial de aniversario (Ejecuta UPSERT)."""
    today = date.today()

    res_event = await db.execute(select(Event).where(Event.id == id))
    event_obj = res_event.scalars().first()

    if not event_obj:
        # Si es un evento virtual, el ID recibido es el client_id; se crea la instancia física
        res_client = await db.execute(select(Client).where(Client.id == id))
        client = res_client.scalars().first()
        if not client:
            raise HTTPException(status_code=404, detail="Cliente o evento no encontrado")

        event_obj = Event(
            client_id=client.id,
            event_type=EventType.ANIVERSARIO.value,
            year=today.year,
            event_date=data.event_date,
            status="REPROGRAMADO"
        )
        db.add(event_obj)
    else:
        event_obj.event_date = data.event_date
        event_obj.status = "REPROGRAMADO"
        db.add(event_obj)

    await db.commit()
    await db.refresh(event_obj)

    return await get_event_detail(id=event_obj.id, current_user=admin_user, db=db)


@router.put("/{id}/resources", response_model=EventResourcesUpdateResponse, summary="Asignar Excepciones de Insumos (Solo ADMIN)")
async def update_event_resources(
    id: uuid.UUID,
    resources_in: List[EventResourceItem],
    admin_user: User = Depends(deps.get_current_admin_user),
    db: AsyncSession = Depends(get_db)
):
    """Reemplaza la lista de SKUs asignados únicamente para la instancia de este año."""
    today = date.today()

    res_event = await db.execute(select(Event).where(Event.id == id))
    event_obj = res_event.scalars().first()

    if not event_obj:
        res_client = await db.execute(select(Client).where(Client.id == id))
        client = res_client.scalars().first()
        if not client:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        official_date = date(today.year, client.anniversary_date.month, client.anniversary_date.day)
        event_obj = Event(
            client_id=client.id,
            event_type=EventType.ANIVERSARIO.value,
            year=today.year,
            event_date=official_date,
            status="CONFIRMADO"
        )
        db.add(event_obj)
        await db.commit()
        await db.refresh(event_obj)
    else:
        event_obj.status = "CONFIRMADO"
        db.add(event_obj)

    # Eliminar asignaciones anteriores de este evento
    await db.execute(select(EventResourceAssigned).where(EventResourceAssigned.event_id == event_obj.id))
    
    total_cost = 0.0
    detail_list = []

    for item in resources_in:
        res_r = await db.execute(select(Resource).where(Resource.id == item.resource_id))
        resource_obj = res_r.scalars().first()
        if not resource_obj:
            raise HTTPException(status_code=404, detail=f"El recurso con ID {item.resource_id} no existe")

        assigned = EventResourceAssigned(
            event_id=event_obj.id,
            resource_id=item.resource_id,
            assigned_quantity=item.assigned_quantity
        )
        db.add(assigned)

        subtotal = item.assigned_quantity * resource_obj.unit_price_usd
        total_cost += subtotal
        detail_list.append(
            EventResourceDetailResponse(
                resource_id=resource_obj.id,
                sku_code=resource_obj.sku_code,
                name=resource_obj.name,
                quantity=item.assigned_quantity,
                unit_price_usd=resource_obj.unit_price_usd,
                total_usd=round(subtotal, 2)
            )
        )

    await db.commit()

    return EventResourcesUpdateResponse(
        event_id=event_obj.id,
        total_resources_count=len(detail_list),
        total_cost_usd=round(total_cost, 2),
        assigned_resources=detail_list
    )