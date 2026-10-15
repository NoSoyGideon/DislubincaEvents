# Archivo: app/schemas/enums.py
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATIVO = "OPERATIVO"

class UserPosition(str, Enum):
    VENDEDOR = "vendedor"
    SUPERVISOR = "supervisor"
    GERENTE = "gerente"
    CONTADOR = "contador"

class ClientClassification(str, Enum):
    TOP_5 = "TOP 5"
    TOP_2 = "TOP 2"
    RESTO = "RESTO"

class EventType(str, Enum):
    ANIVERSARIO = "ANIVERSARIO"
    CUMPLEANOS_DUENO = "CUMPLEANOS_DUENO"