# CORRECCIÓN APLICADA: [1 — Autenticación en endpoints]
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.produccion.schemas import ProduccionCreate, ProduccionUpdate
from app.modules.produccion.service import ProduccionService

router = APIRouter(prefix="/produccion", tags=["Produccion"])


@router.get(
    "",
    summary="Listar producción",
    description="Retorna todos los registros de producción activos.",
)
async def list_produccion(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ProduccionService.list(db)
    return success_response(
        message="Produccion obtenida",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/rango",
    summary="Listar producción por rango",
    description="Retorna registros de producción filtrados por fecha de inicio y fin.",
)
async def list_produccion_rango(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    fecha_inicio: Annotated[datetime, Query(...)],
    fecha_fin: Annotated[datetime, Query(...)],
) -> dict:
    data = await ProduccionService.list_rango(db, fecha_inicio, fecha_fin)
    return success_response(
        message="Produccion por rango obtenida",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/galpon/{galpon_id}",
    summary="Listar producción por galpón",
    description="Retorna registros de producción asociados a un galpón.",
)
async def list_produccion_galpon(
    galpon_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ProduccionService.list_por_galpon(db, galpon_id)
    return success_response(
        message="Produccion por galpon obtenida",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/promedios",
    summary="Promedios de producción por periodo",
    description="Agrupa la producción de un lote por periodo semanal o mensual.",
)
async def get_promedios(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    lote_id: Annotated[str, Query(min_length=36, max_length=36)],
    periodo: Annotated[Literal["semanal", "mensual"], Query(...)],
) -> dict:
    data = await ProduccionService.get_promedios(db, lote_id=lote_id, periodo=periodo)
    return success_response(
        message="Promedios de produccion obtenidos",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/{produccion_id}",
    summary="Obtener producción",
    description="Retorna el detalle de un registro de producción.",
)
async def get_produccion(
    produccion_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ProduccionService.get_by_id(db, produccion_id)
    return success_response(message="Produccion obtenida", data=data.model_dump())


@router.post(
    "",
    summary="Crear producción",
    description="Registra un nuevo evento de producción de huevo.",
)
async def create_produccion(
    payload: ProduccionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ProduccionService.create(db, payload)
    return success_response(message="Produccion creada", data=data.model_dump())


@router.put(
    "/{produccion_id}",
    summary="Actualizar producción",
    description="Modifica un registro de producción existente.",
)
async def update_produccion(
    produccion_id: str,
    payload: ProduccionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await ProduccionService.update(db, produccion_id, payload)
    return success_response(message="Produccion actualizada", data=data.model_dump())


@router.delete(
    "/{produccion_id}",
    summary="Eliminar producción",
    description="Realiza soft delete del registro de producción.",
)
async def delete_produccion(
    produccion_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    await ProduccionService.delete(db, produccion_id)
    return success_response(message="Produccion eliminada", data=None)
