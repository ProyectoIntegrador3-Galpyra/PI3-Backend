from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.core.responses import success_response
from app.modules.admin.schemas import UsuarioCreateRequest, UsuarioUpdateRequest
from app.modules.admin.service import AdminService
from app.modules.auth.models import Usuario

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/users",
    summary="Listar usuarios",
    description="Retorna todos los usuarios del sistema. Requiere rol ADMIN.",
)
async def list_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
) -> dict:
    data = await AdminService.list_users(db)
    return success_response(message="Usuarios obtenidos", data=[u.model_dump() for u in data])


@router.post(
    "/users",
    status_code=201,
    summary="Crear usuario",
    description="Crea un nuevo usuario. Requiere rol ADMIN.",
)
async def create_user(
    payload: UsuarioCreateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
) -> dict:
    data = await AdminService.create_user(db, payload)
    return success_response(message="Usuario creado", data=data.model_dump(), status_code=201)


@router.patch(
    "/users/{user_id}",
    summary="Actualizar usuario",
    description="Actualiza nombre, email, contraseña o rol. Requiere rol ADMIN.",
)
async def update_user(
    user_id: str,
    payload: UsuarioUpdateRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
) -> dict:
    data = await AdminService.update_user(db, user_id, payload)
    return success_response(message="Usuario actualizado", data=data.model_dump())


@router.delete(
    "/users/{user_id}",
    status_code=200,
    summary="Eliminar usuario",
    description="Soft-delete de usuario. No puede eliminar su propio usuario. Requiere rol ADMIN.",
)
async def delete_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
) -> dict:
    await AdminService.delete_user(db, user_id, current_user.id)
    return success_response(message="Usuario eliminado")
