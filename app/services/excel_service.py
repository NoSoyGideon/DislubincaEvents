from fastapi import UploadFile
from app.schemas.client_schema import ExcelImportResponse

async def process_excel_import_stub(file: UploadFile) -> ExcelImportResponse:
    """
    Stub temporal para el módulo de carga de Excel.
    Se implementará con Pandas/OpenPyXL una vez recibida la plantilla oficial.
    """
    return ExcelImportResponse(
        created=0,
        updated=0,
        total_processed=0,
        errors=["Módulo de importación en espera de la plantilla oficial del CRM."]
    )