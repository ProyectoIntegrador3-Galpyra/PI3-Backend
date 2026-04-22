from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth.models import RefreshToken, Usuario
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    UsuarioOut,
)


class AuthService:
    @staticmethod
    async def login(db: AsyncSession, payload: LoginRequest) -> LoginResponse:
        query = select(Usuario).where(
            Usuario.email == payload.email,
            Usuario.deleted_at.is_(None),
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise AppException(
                message="Credenciales invalidas",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        if not verify_password(payload.password, user.password_hash):
            raise AppException(
                message="Credenciales invalidas",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        access_token = create_access_token(subject=user.id, rol=user.rol.value)
        refresh_token, refresh_hash, refresh_expires_at = create_refresh_token()

        db_refresh = RefreshToken(
            user_id=user.id,
            token_hash=refresh_hash,
            expires_at=refresh_expires_at,
        )
        db.add(db_refresh)
        await db.commit()

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UsuarioOut.model_validate(user),
        )

    @staticmethod
    async def refresh(db: AsyncSession, payload: RefreshRequest) -> RefreshResponse:
        token_hash = hash_refresh_token(payload.refresh_token)

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.deleted_at.is_(None),
            )
        )
        refresh_row = result.scalar_one_or_none()

        if refresh_row is None:
            raise AppException(
                message="Refresh token invalido",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        now = datetime.now(timezone.utc)
        expires_at = refresh_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if refresh_row.revoked_at is not None or expires_at < now:
            raise AppException(
                message="Refresh token expirado o revocado",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        user_result = await db.execute(
            select(Usuario).where(
                Usuario.id == refresh_row.user_id, Usuario.deleted_at.is_(None)
            )
        )
        user = user_result.scalar_one_or_none()
        if user is None or not user.is_active:
            raise AppException(
                message="Usuario no disponible",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        refresh_row.revoked_at = now

        new_access_token = create_access_token(subject=user.id, rol=user.rol.value)
        new_refresh_token, new_hash, new_expires_at = create_refresh_token()
        db.add(
            RefreshToken(
                user_id=user.id,
                token_hash=new_hash,
                expires_at=new_expires_at,
            )
        )

        await db.commit()

        return RefreshResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    @staticmethod
    async def logout(db: AsyncSession, payload: LogoutRequest) -> None:
        token_hash = hash_refresh_token(payload.refresh_token)

        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash,
                RefreshToken.deleted_at.is_(None),
            )
        )
        refresh_row = result.scalar_one_or_none()

        if refresh_row is None:
            return

        refresh_row.revoked_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def me(user: Usuario) -> UsuarioOut:
        return UsuarioOut.model_validate(user)
