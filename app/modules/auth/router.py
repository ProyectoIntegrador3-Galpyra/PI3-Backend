from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import LoginRequest, LogoutRequest, RefreshRequest
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/login",
    summary="Iniciar sesión",
    description="Autentica al usuario y retorna access token y refresh token.",
)
async def login(
    payload: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    data = await AuthService.login(db, payload)
    return success_response(message="Login exitoso", data=data.model_dump())


@router.post(
    "/refresh",
    summary="Refrescar token",
    description="Genera un nuevo access token usando el refresh token.",
)
async def refresh(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    data = await AuthService.refresh(db, payload)
    return success_response(message="Token refrescado", data=data.model_dump())


@router.post(
    "/logout",
    summary="Cerrar sesión",
    description="Invalida el refresh token del usuario.",
)
async def logout(
    payload: LogoutRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    await AuthService.logout(db, payload)
    return success_response(message="Sesion cerrada", data=None)


@router.get(
    "/me",
    summary="Perfil del usuario",
    description="Retorna los datos del usuario autenticado.",
)
async def me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> dict:
    user = await AuthService.me(current_user)
    return success_response(message="Perfil obtenido", data=user.model_dump())
