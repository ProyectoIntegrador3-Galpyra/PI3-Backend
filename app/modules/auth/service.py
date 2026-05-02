from datetime import datetime, timedelta, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import secrets

from app.core.exceptions import AppException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    verify_password,
    hash_password,
)
from app.modules.auth.models import RefreshToken, Usuario, PasswordResetToken
from app.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RefreshResponse,
    UsuarioOut,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
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

    @staticmethod
    async def forgot_password(
        db: AsyncSession,
        payload: ForgotPasswordRequest,
    ) -> ForgotPasswordResponse:
        """Genera y envía token de reset de contraseña por email."""
        # Buscar usuario por email
        query = select(Usuario).where(
            Usuario.email == payload.email,
            Usuario.deleted_at.is_(None),
        )
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        # Respuesta genérica: nunca revelar si el email existe o no
        generic_response = ForgotPasswordResponse(
            message="Si el correo está registrado, recibirás un enlace en los próximos minutos."
        )

        if user is None or not user.is_active:
            return generic_response

        # Generar token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=180  # 3 horas para que el email se resuelva
        )

        db_token = PasswordResetToken(
            usuario_id=user.id,
            token=token,
            expires_at=expires_at,
        )
        db.add(db_token)
        await db.commit()

        from app.core.email_service import send_password_reset_email
        await send_password_reset_email(
            email_to=user.email,
            nombre=user.nombre or user.email.split("@")[0],
            token=token,
        )

        return generic_response

    @staticmethod
    async def reset_password(
        db: AsyncSession,
        payload: ResetPasswordRequest,
    ) -> ResetPasswordResponse:
        """Verifica token y actualiza contraseña."""
        now = datetime.now(timezone.utc)

        # Buscar token válido no usado y no expirado
        query = select(PasswordResetToken).where(
            PasswordResetToken.token == payload.token,
            PasswordResetToken.usado.is_(False),
        )
        result = await db.execute(query)
        token_row = result.scalar_one_or_none()

        if token_row is None:
            raise AppException(
                message="Token inválido o expirado",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Verificar expiración
        expires_at = token_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            raise AppException(
                message="Token inválido o expirado",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Buscar usuario
        user_result = await db.execute(
            select(Usuario).where(
                Usuario.id == token_row.usuario_id,
                Usuario.deleted_at.is_(None),
            )
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            raise AppException(
                message="Token inválido o expirado",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Actualizar contraseña y marcar token como usado
        user.password_hash = hash_password(payload.nueva_password)
        user.updated_at = now
        token_row.usado = True

        await db.commit()

        return ResetPasswordResponse(message="Contraseña actualizada exitosamente")
