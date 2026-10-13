from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_maker
from app.core.security import get_password_hash
from app.models.route import Route
from app.models.user import User

# Rutas estándar fijas de la empresa Dislubinca
INITIAL_ROUTES = [10, 15, 17, 21, 26, 30, 32, 39]

async def init_initial_data() -> None:
    """Crea los datos mínimos indispensables si la base de datos está vacía."""
    async with async_session_maker() as db:
        # 1. Autocreación de Rutas
        for route_number in INITIAL_ROUTES:
            result = await db.execute(select(Route).where(Route.number == route_number))
            existing_route = result.scalars().first()
            if not existing_route:
                db.add(Route(number=route_number))
        
        # 2. Autocreación del Administrador Principal Inicial
        admin_email = "soporte@dislubinca.com"
        result_user = await db.execute(select(User).where(User.email == admin_email))
        existing_admin = result_user.scalars().first()
        
        if not existing_admin:
            admin_user = User(
                name="Admin",
                email=admin_email,
                password_hash=get_password_hash("Admin2312*"), # Cambiar en primer login
                role="ADMIN",
                position="gerente",
                is_active=True
            )
            db.add(admin_user)
        
        await db.commit()
        print("✅ Datos semilla (Rutas y Admin inicial) verificados/creados exitosamente.")