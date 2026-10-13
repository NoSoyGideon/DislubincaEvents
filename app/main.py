from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
import app.models  # Registra los modelos en SQLModel antes de init_db()
from app.api.v1.api import api_router
from app.core.initial_data import init_initial_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Evento de Inicio (Startup): Crea las tablas en PostgreSQL si no existen
    await init_db()
    await init_initial_data()
    yield
    # Evento de Cierre (Shutdown): Limpieza de recursos si fuera necesario

    # Aquí puedes agregar lógica de limpieza si es necesario


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Configuración de CORS para clientes móviles React Native (Expo)[cite: 2, 3]
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar enrutadores de la versión 1 (/api/v1)[cite: 2, 3]
app.include_router(api_router, prefix=settings.API_V1_STR)


# Endpoint Global de Verificación de Salud
@app.get("/healthcheck", tags=["Health"])
async def health_check():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database": "connected",
    }