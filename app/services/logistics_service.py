from typing import Dict, List, Any
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, extract

from app.models.client import Client, ClientBaseResource
from app.models.event import Event, EventResourceAssigned
from app.models.resource import Resource
from app.models.route import Route
from app.schemas.logistics_schema import MonthlySummaryResponse, MonthlyItemSummary

async def build_monthly_summary_report(
    db: AsyncSession,
    month: int,
    year: int,
    route_number: Optional[int] = None,
    classification: Optional[str] = None
) -> MonthlySummaryResponse:
    """Calcula las métricas consolidadas, lista de compras por SKU y desglose por clasificación."""
    
    # 1. Consultar clientes activos con aniversario en el mes
    query_clients = select(Client).where(
        Client.is_active == True,
        extract('month', Client.anniversary_date) == month
    )

    if route_number is not None:
        res_route = await db.execute(select(Route).where(Route.number == route_number))
        route_obj = res_route.scalars().first()
        if route_obj:
            query_clients = query_clients.where(Client.route_id == route_obj.id)
        else:
            # Si la ruta no existe, retornar reporte en cero
            return MonthlySummaryResponse(
                month=month, year=year, total_events=0, events_pending=0,
                total_cost_usd=0.0, budget_by_classification={"TOP 5": 0.0, "TOP 2": 0.0, "RESTO": 0.0},
                items_summary=[]
            )

    if classification:
        query_clients = query_clients.where(Client.classification == classification)

    res_clients = await db.execute(query_clients)
    clients = res_clients.scalars().all()

    total_events = len(clients)
    events_pending = 0
    total_cost_usd = 0.0
    
    budget_by_class: Dict[str, float] = {"TOP 5": 0.0, "TOP 2": 0.0, "RESTO": 0.0}
    items_map: Dict[str, Dict[str, Any]] = {}

    for client in clients:
        # Buscar si el evento ya existe en BD para ese año
        res_event = await db.execute(
            select(Event).where(
                Event.client_id == client.id,
                Event.year == year
            )
        )
        event_obj = res_event.scalars().first()

        client_class = client.classification

        if not event_obj or event_obj.status == "PENDIENTE":
            events_pending += 1
            # Leer insumos base del cliente
            res_base = await db.execute(
                select(ClientBaseResource, Resource)
                .join(Resource, ClientBaseResource.resource_id == Resource.id)
                .where(ClientBaseResource.client_id == client.id)
            )
            for b_res, resource in res_base.all():
                qty = b_res.quantity
                cost = qty * resource.unit_price_usd
                total_cost_usd += cost
                budget_by_class[client_class] = budget_by_class.get(client_class, 0.0) + cost

                r_id_str = str(resource.id)
                if r_id_str not in items_map:
                    items_map[r_id_str] = {
                        "resource_id": resource.id,
                        "sku_code": resource.sku_code,
                        "name": resource.name,
                        "total_quantity": 0,
                        "unit_price_usd": resource.unit_price_usd,
                        "total_usd": 0.0
                    }
                items_map[r_id_str]["total_quantity"] += qty
                items_map[r_id_str]["total_usd"] += cost

        else:
            # Leer insumos de la excepción de evento asignado
            res_assigned = await db.execute(
                select(EventResourceAssigned, Resource)
                .join(Resource, EventResourceAssigned.resource_id == Resource.id)
                .where(EventResourceAssigned.event_id == event_obj.id)
            )
            for a_res, resource in res_assigned.all():
                qty = a_res.assigned_quantity
                cost = qty * resource.unit_price_usd
                total_cost_usd += cost
                budget_by_class[client_class] = budget_by_class.get(client_class, 0.0) + cost

                r_id_str = str(resource.id)
                if r_id_str not in items_map:
                    items_map[r_id_str] = {
                        "resource_id": resource.id,
                        "sku_code": resource.sku_code,
                        "name": resource.name,
                        "total_quantity": 0,
                        "unit_price_usd": resource.unit_price_usd,
                        "total_usd": 0.0
                    }
                items_map[r_id_str]["total_quantity"] += qty
                items_map[r_id_str]["total_usd"] += cost

    # Formatear lista de items redondeando montos
    summary_items = []
    for item in items_map.values():
        summary_items.append(
            MonthlyItemSummary(
                resource_id=item["resource_id"],
                sku_code=item["sku_code"],
                name=item["name"],
                total_quantity=item["total_quantity"],
                unit_price_usd=item["unit_price_usd"],
                total_usd=round(item["total_usd"], 2)
            )
        )

    # Redondear montos de clasificaciones
    formatted_budget_class = {k: round(v, 2) for k, v in budget_by_class.items()}

    return MonthlySummaryResponse(
        month=month,
        year=year,
        total_events=total_events,
        events_pending=events_pending,
        total_cost_usd=round(total_cost_usd, 2),
        budget_by_classification=formatted_budget_class,
        items_summary=summary_items
    )