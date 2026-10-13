from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from app.core.config import settings

# Optimized asyncronus engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True, 
    future=True,
)

async_session_maker = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Tables Creation
async def init_db() -> None:
    async with engine.begin() as conn:
        # Crea todas las tablas mapeadas en SQLModel si no existen
        await conn.run_sync(SQLModel.metadata.create_all)

# Inyección de Dependencia para Endpoints de FastAPI
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session