from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_admin
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.reportes.analytics import ReportesAnalyticsService
from app.modules.reportes.schemas import (
    ReporteGenerarRequest,
    DescargarReporteResponse,
)
from app.modules.reportes.service import ReportesService

router = APIRouter(prefix="/reportes", tags=["Reportes"])


def _reporte_payload(item) -> dict:
    payload = item.model_dump()
    payload["url_reporte"] = payload.get("url_archivo")
    return payload


# ── Rutas estáticas ANTES de /{reporte_id} para evitar conflicto de captura ──

@router.get(
    "",
    summary="Listar reportes",
    description="Retorna los reportes generados y disponibles.",
)
async def list_reportes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ReportesService.list(db)
    return success_response(
        message="Reportes obtenidos",
        data=[_reporte_payload(item) for item in data],
    )


@router.post(
    "/generar",
    summary="Generar reporte",
    description="Genera un reporte PDF y registra su ubicación.",
)
async def generar_reporte(
    payload: ReporteGenerarRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ReportesService.generar(db, payload)
    return success_response(message="Reporte generado", data=_reporte_payload(data))


@router.get(
    "/produccion",
    summary="Reporte de producción",
    description="Producción de huevos agrupada por período. Requiere rol ADMIN.",
)
async def reporte_produccion(
    anio: Annotated[int, Query(ge=2000, le=2100)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    galpon_id: str | None = None,
) -> dict:
    data = await ReportesAnalyticsService.produccion(db, anio, mes, galpon_id)
    return success_response(message="Reporte de producción obtenido", data=data)


@router.get(
    "/alimentacion",
    summary="Reporte de alimentación",
    description="Consumo y costo de alimento agrupado por período. Requiere rol ADMIN.",
)
async def reporte_alimentacion(
    anio: Annotated[int, Query(ge=2000, le=2100)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    galpon_id: str | None = None,
) -> dict:
    data = await ReportesAnalyticsService.alimentacion(db, anio, mes, galpon_id)
    return success_response(message="Reporte de alimentación obtenido", data=data)


@router.get(
    "/mortalidad",
    summary="Reporte de mortalidad",
    description="Bajas y tasa de mortalidad agrupadas por período. Requiere rol ADMIN.",
)
async def reporte_mortalidad(
    anio: Annotated[int, Query(ge=2000, le=2100)],
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
    mes: Annotated[int | None, Query(ge=1, le=12)] = None,
    galpon_id: str | None = None,
) -> dict:
    data = await ReportesAnalyticsService.mortalidad(db, anio, mes, galpon_id)
    return success_response(message="Reporte de mortalidad obtenido", data=data)


@router.get(
    "/inventario",
    summary="Reporte de inventario",
    description="Estado actual de aves por galpón y lote. Requiere rol ADMIN.",
)
async def reporte_inventario(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
    galpon_id: str | None = None,
) -> dict:
    data = await ReportesAnalyticsService.inventario(db, galpon_id)
    return success_response(message="Reporte de inventario obtenido", data=data)


# ── Ruta dinámica al final para no capturar las rutas estáticas de arriba ────

@router.get(
    "/{reporte_id}/descargar",
    summary="Descargar reporte",
    description="Genera URL presignada S3 para descargar el reporte PDF.",
)
async def descargar_reporte(
    reporte_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ReportesService.get_download_url(db, reporte_id, current_user)
    return success_response(
        message="URL de descarga generada",
        data=data.model_dump(),
    )


@router.get(
    "/{reporte_id}",
    summary="Obtener reporte",
    description="Retorna el detalle de un reporte generado.",
)
async def get_reporte(
    reporte_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ReportesService.get_by_id(db, reporte_id)
    return success_response(message="Reporte obtenido", data=_reporte_payload(data))
