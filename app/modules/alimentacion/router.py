# CORRECCIÓN APLICADA: [1 — Autenticación en endpoints]
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.alimentacion.schemas import AlimentacionCreate, AlimentacionUpdate
from app.modules.alimentacion.service import AlimentacionService
from app.modules.auth.models import Usuario

router = APIRouter(prefix="/alimentacion", tags=["Alimentacion"])


@router.get(
    "",
    summary="Listar alimentación",
    description="Retorna todos los registros de alimentación activos.",
)
async def list_alimentacion(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AlimentacionService.list(db)
    return success_response(
        message="Registros de alimentacion obtenidos",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/rango",
    summary="Listar alimentación por rango",
    description="Retorna registros de alimentación filtrados por fechas.",
)
async def list_alimentacion_rango(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    fecha_inicio: Annotated[datetime, Query(...)],
    fecha_fin: Annotated[datetime, Query(...)],
) -> dict:
    data = await AlimentacionService.list_rango(db, fecha_inicio, fecha_fin)
    return success_response(
        message="Registros de alimentacion por rango obtenidos",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/conversion/{lote_id}",
    summary="Calcular conversión alimenticia",
    description="Calcula la conversión alimenticia de un lote en un rango opcional.",
)
async def get_conversion_alimenticia(
    lote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    fecha_inicio: Annotated[datetime | None, Query()] = None,
    fecha_fin: Annotated[datetime | None, Query()] = None,
) -> dict:
    data = await AlimentacionService.calcular_conversion_alimenticia(
        db,
        lote_id=lote_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    return success_response(
        message="Conversion alimenticia obtenida",
        data=data.model_dump(),
    )


@router.get(
    "/{registro_id}",
    summary="Obtener registro de alimentación",
    description="Retorna el detalle de un registro de alimentación.",
)
async def get_alimentacion(
    registro_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AlimentacionService.get_by_id(db, registro_id)
    return success_response(
        message="Registro de alimentacion obtenido", data=data.model_dump()
    )


@router.post(
    "",
    summary="Crear registro de alimentación",
    description="Registra un nuevo consumo de alimento.",
)
async def create_alimentacion(
    payload: AlimentacionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AlimentacionService.create(db, payload)
    return success_response(
        message="Registro de alimentacion creado", data=data.model_dump()
    )


@router.put(
    "/{registro_id}",
    summary="Actualizar registro de alimentación",
    description="Modifica un registro de alimentación existente.",
)
async def update_alimentacion(
    registro_id: str,
    payload: AlimentacionUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AlimentacionService.update(db, registro_id, payload)
    return success_response(
        message="Registro de alimentacion actualizado", data=data.model_dump()
    )


@router.delete(
    "/{registro_id}",
    summary="Eliminar registro de alimentación",
    description="Realiza soft delete del registro de alimentación.",
)
async def delete_alimentacion(
    registro_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    await AlimentacionService.delete(db, registro_id)
    return success_response(message="Registro de alimentacion eliminado", data=None)
