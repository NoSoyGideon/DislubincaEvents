import asyncio
from datetime import date
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.route import Route
from app.models.client import Client
from app.models.resource import Resource


'''Poblar Datos de Prueba: Ejecutas en tu terminal:

                    python -m scripts.seed_test_data


Limpiar Datos de Prueba Ejecutas en tu terminal:

                    python -m scripts.seed_test_data --clear
                    
                    
'''


async def seed_test_data():
    """Inserta clientes y SKUs de prueba."""
    async with async_session_maker() as db:
        # Obtener ID de la Ruta 10
        route_res = await db.execute(select(Route).where(Route.number == 10))
        route_10 = route_res.scalars().first()
        
        if not route_10:
            print("❌ Primero debes correr los datos semilla.")
            return

        # 1. SKUs de Prueba
        skus = [
            Resource(sku_code="CAM-POLO-L", name="Camisa Polo Tipo L", unit_price_usd=8.50),
            Resource(sku_code="AFICHE-DIS", name="Afiche Publicitario Dislubinca", unit_price_usd=2.00),
            Resource(sku_code="EST-EXH-01", name="Estante Exhibidor Lubricantes", unit_price_usd=45.00),
        ]
        for sku in skus:
            db.add(sku)
            
        # 2. Clientes de Prueba
        clients = [
            Client(
                rif="J-12345678-0",
                id_crm="CRM-101",
                name="Inversiones El Sol C.A.",
                anniversary_date=date(2018, 10, 15), # Aniversario en Octubre
                owner_name="Carlos Mendoza",
                owner_birthdate=date(1985, 10, 20),
                classification="TOP 5",
                route_id=route_10.id,
                zone="centro 1",
                address="Av. Las Delicias, Local 12",
                phone="0414-1234567"
            ),
            Client(
                rif="J-87654321-9",
                id_crm="CRM-102",
                name="Repuestos Maracaibo R.L.",
                anniversary_date=date(2020, 10, 18),
                classification="TOP 2",
                route_id=route_10.id,
                zone="sur 1",
                address="Zona Industrial",
                phone="0424-7654321"
            )
        ]
        for c in clients:
            db.add(c)
            
        await db.commit()
        print("🚀 Datos de prueba insertados exitosamente.")

async def clear_test_data():
    """Elimina clientes y SKUs de prueba a voluntad."""
    async with async_session_maker() as db:
        # Borra clientes y recursos de prueba sin tocar usuarios ni rutas
        await db.execute("DELETE FROM client_base_resources;")
        await db.execute("DELETE FROM event_resource_assigned;")
        await db.execute("DELETE FROM events;")
        await db.execute("DELETE FROM clients;")
        await db.execute("DELETE FROM resources;")
        await db.commit()
        print("🧹 Base de datos limpia de datos de prueba.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        asyncio.run(clear_test_data())
    else:
        asyncio.run(seed_test_data())
        
        
        

        