from fastapi import APIRouter
from app.api.v1.endpoints import auth, clients, users

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación & Seguridad"])
api_router.include_router(users.router, prefix="/users", tags=["Gestión de Usuarios"])
api_router.include_router(clients.router, prefix="/clients", tags=["Gestión de Clientes"])