# CORRECCIÓN APLICADA: [1 — Autenticación en endpoints]
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.sync.schemas import SyncRequest
from app.modules.sync.service import SyncService

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post(
    "",
    summary="Procesar sincronización",
    description="Procesa un lote de operaciones offline con estrategia Last Write Wins.",
)
async def process_sync(
    payload: SyncRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    result = await SyncService.procesar_batch(db, payload)
    return success_response(message="Sync procesado", data=result.model_dump())


@router.get(
    "/logs",
    summary="Listar logs de sync",
    description="Retorna el historial de procesamiento de operaciones de sincronización.",
)
async def list_sync_logs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await SyncService.list_logs(db)
    return success_response(
        message="Logs de sync obtenidos",
        data=[item.model_dump() for item in data],
    )
