# CORRECCIÓN APLICADA: [1 — Autenticación en endpoints]
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.inventario_foto.schemas import InventarioConfirmarRequest
from app.modules.inventario_foto.service import InventarioFotoService

router = APIRouter(prefix="/inventario", tags=["Inventario Foto"])


@router.post(
    "/procesar",
    summary="Procesar inventario por foto",
    description="Procesa una imagen para estimar el conteo de aves mediante YOLO o conteo simulado.",
)
async def procesar_inventario_foto(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
    imagen: Annotated[UploadFile | None, File()] = None,
    file: Annotated[UploadFile | None, File()] = None,
    lote_id: Annotated[str | None, Form()] = None,
    galpon_id: Annotated[str | None, Form()] = None,
) -> dict:
    upload = imagen or file
    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Debe enviar una imagen en el campo 'imagen' o 'file'",
        )

    data = await InventarioFotoService.procesar_imagen(db, upload, lote_id, galpon_id)
    return success_response(message="Imagen procesada", data=data.model_dump())


@router.post(
    "/confirmar",
    summary="Confirmar conteo de inventario",
    description="Confirma manualmente el conteo estimado de un job de inventario.",
)
async def confirmar_inventario_foto(
    payload: InventarioConfirmarRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await InventarioFotoService.confirmar_conteo(db, payload)
    return success_response(message="Conteo confirmado", data=data.model_dump())


@router.get(
    "/jobs",
    summary="Listar jobs de inventario",
    description="Retorna los jobs de inventario procesados o pendientes.",
)
async def list_jobs(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await InventarioFotoService.list_jobs(db)
    return success_response(
        message="Jobs de inventario obtenidos",
        data=[item.model_dump() for item in data],
    )


@router.get(
    "/jobs/{job_id}",
    summary="Obtener job de inventario",
    description="Retorna el detalle de un job de inventario por ID.",
)
async def get_job(
    job_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    data = await InventarioFotoService.get_job(db, job_id)
    return success_response(
        message="Job de inventario obtenido", data=data.model_dump()
    )
