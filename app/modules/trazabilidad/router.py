from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.trazabilidad.schemas import TokenTrazabilidadCreate
from app.modules.trazabilidad.service import TrazabilidadService

router = APIRouter(prefix="/trazabilidad", tags=["Trazabilidad"])


@router.post("/token")
async def generar_token(
    payload: TokenTrazabilidadCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    usuario: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await TrazabilidadService.generar_token(db, payload, usuario.id)
    return success_response(message="Token generado", data=data.model_dump())


@router.get("/{token}")
async def consultar_trazabilidad(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    data = await TrazabilidadService.consultar_por_token(db, token)
    return success_response(message="Historial de trazabilidad", data=data)
