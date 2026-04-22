# CORRECCIÓN APLICADA: [1 — Autenticación en endpoints]
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.galpones.schemas import GalponCreate, GalponUpdate
from app.modules.galpones.service import GalponService

router = APIRouter(prefix="/galpones", tags=["Galpones"])


@router.get(
    "",
    summary="Listar galpones",
    description="Retorna todos los galpones activos del sistema.",
)
async def list_galpones(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await GalponService.list(db)
    return success_response(
        message="Galpones obtenidos",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/{galpon_id}/lotes",
    summary="Listar lotes de un galpón",
    description="Retorna los lotes activos asociados al galpón.",
)
async def list_lotes_by_galpon(
    galpon_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await GalponService.list_lotes_by_galpon(db, galpon_id)
    return success_response(
        message="Lotes del galpon obtenidos",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/{galpon_id}",
    summary="Obtener galpón",
    description="Retorna el detalle de un galpón por su ID.",
)
async def get_galpon(
    galpon_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await GalponService.get_by_id(db, galpon_id)
    return success_response(message="Galpon obtenido", data=data.model_dump())


@router.post(
    "",
    summary="Crear galpón",
    description="Registra un nuevo galpón.",
)
async def create_galpon(
    payload: GalponCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await GalponService.create(db, payload)
    return success_response(message="Galpon creado", data=data.model_dump())


@router.put(
    "/{galpon_id}",
    summary="Actualizar galpón",
    description="Modifica capacidad, estado u otros campos del galpón.",
)
async def update_galpon(
    galpon_id: str,
    payload: GalponUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await GalponService.update(db, galpon_id, payload)
    return success_response(message="Galpon actualizado", data=data.model_dump())


@router.delete(
    "/{galpon_id}",
    summary="Eliminar galpón",
    description="Realiza soft delete del galpón (no borra físicamente).",
)
async def delete_galpon(
    galpon_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    await GalponService.delete(db, galpon_id)
    return success_response(message="Galpon eliminado", data=None)
