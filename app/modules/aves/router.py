# CORRECCIÓN APLICADA: [1 — Autenticación en endpoints]
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.aves.schemas import (
    LoteAveCreate,
    LoteAveUpdate,
    MovimientoIngresoCreate,
    MovimientoMortalidadCreate,
)
from app.modules.aves.service import AvesService
from app.shared.enums import TipoMovimientoAve

router = APIRouter(tags=["Aves"])


@router.get(
    "/lotes",
    summary="Listar lotes",
    description="Retorna todos los lotes activos del sistema.",
)
async def list_lotes(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AvesService.list_lotes(db)
    return success_response(
        message="Lotes obtenidos", data=[item.model_dump() for item in data]
    )


@router.get(
    "/lotes/galpon/{galpon_id}",
    summary="Listar lotes por galpón",
    description="Retorna los lotes activos asociados a un galpón.",
)
async def list_lotes_por_galpon(
    galpon_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AvesService.list_lotes_por_galpon(db, galpon_id)
    return success_response(
        message="Lotes por galpon obtenidos",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/lotes/{lote_id}",
    summary="Obtener lote",
    description="Retorna el detalle de un lote por su ID.",
)
async def get_lote(
    lote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AvesService.get_lote(db, lote_id)
    return success_response(message="Lote obtenido", data=data.model_dump())


@router.get(
    "/lotes/{lote_id}/mortalidad",
    summary="Historial de mortalidad",
    description="Retorna el historial de mortalidad del lote con filtros opcionales de fecha.",
)
async def historial_mortalidad(
    lote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    fecha_inicio: Annotated[datetime | None, Query()] = None,
    fecha_fin: Annotated[datetime | None, Query()] = None,
) -> dict:
    data = await AvesService.historial_mortalidad(
        db,
        lote_id=lote_id,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    return success_response(
        message="Historial de mortalidad obtenido", data=data.model_dump()
    )


@router.post(
    "/lotes",
    summary="Crear lote",
    description="Registra un nuevo lote de aves.",
)
async def create_lote(
    payload: LoteAveCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AvesService.create_lote(db, payload)
    return success_response(message="Lote creado", data=data.model_dump())


@router.put(
    "/lotes/{lote_id}",
    summary="Actualizar lote",
    description="Modifica los datos de un lote existente.",
)
async def update_lote(
    lote_id: str,
    payload: LoteAveUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AvesService.update_lote(db, lote_id, payload)
    return success_response(message="Lote actualizado", data=data.model_dump())


@router.delete(
    "/lotes/{lote_id}",
    summary="Eliminar lote",
    description="Realiza soft delete del lote.",
)
async def delete_lote(
    lote_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    await AvesService.delete_lote(db, lote_id)
    return success_response(message="Lote eliminado", data=None)


@router.post(
    "/ingresos",
    summary="Registrar ingreso",
    description="Registra un movimiento de ingreso de aves en un lote.",
)
async def registrar_ingreso(
    payload: MovimientoIngresoCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AvesService.registrar_movimiento(
        db,
        payload=payload,
        tipo_forzado=TipoMovimientoAve.INGRESO,
    )
    return success_response(message="Ingreso registrado", data=data.model_dump())


@router.post(
    "/mortalidad",
    summary="Registrar mortalidad",
    description="Registra un movimiento de mortalidad de aves en un lote.",
)
async def registrar_mortalidad(
    payload: MovimientoMortalidadCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await AvesService.registrar_movimiento(
        db,
        payload=payload,
        tipo_forzado=TipoMovimientoAve.MORTALIDAD,
    )
    return success_response(message="Mortalidad registrada", data=data.model_dump())
