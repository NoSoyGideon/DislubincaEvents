from datetime import date
from typing import Dict, Any, List, Optional

def calculate_days_remaining(event_date: date, target_date: Optional[date] = None) -> int:
    """Calcula la diferencia de días entre la fecha del evento y la fecha objetivo (hoy por defecto)."""
    ref_date = target_date or date.today()
    return (event_date - ref_date).days

def resolve_event_status(has_event_record: bool, event_obj: Any) -> str:
    """Resuelve el estado del evento (REPROGRAMADO, CONFIRMADO o PENDIENTE)."""
    if not has_event_record or not event_obj:
        return "PENDIENTE"
    return event_obj.status

def resolve_next_event_date(orig_date: date, ref_date: Optional[date] = None, include_past_days: int = 15) -> tuple[date, int]:
    """
    Calcula la fecha efectiva del evento para el año activo o para el año siguiente 
    si ya transcurrió en el año actual (ej: 25 de Diciembre evaluando Enero).
    """
    today = ref_date or date.today()
    
    # Evaluar primero en el año actual
    candidate_date = date(today.year, orig_date.month, orig_date.day)
    days_rem = (candidate_date - today).days
    
    # Si la fecha ya pasó este año y supera el margen de días pasados permitidos, proyectar al año siguiente
    if days_rem < -include_past_days:
        candidate_date = date(today.year + 1, orig_date.month, orig_date.day)
        days_rem = (candidate_date - today).days
        
    return candidate_date, days_rem