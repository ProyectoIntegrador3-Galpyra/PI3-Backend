from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.security import hash_password
from app.modules.admin.schemas import UsuarioAdminOut, UsuarioCreateRequest, UsuarioUpdateRequest
from app.modules.auth.models import Usuario


class AdminService:
    @staticmethod
    async def list_users(db: AsyncSession) -> list[UsuarioAdminOut]:
        result = await db.execute(
            select(Usuario)
            .where(Usuario.deleted_at.is_(None))
            .order_by(Usuario.created_at.asc())
        )
        return [UsuarioAdminOut.model_validate(u) for u in result.scalars().all()]

    @staticmethod
    async def create_user(db: AsyncSession, payload: UsuarioCreateRequest) -> UsuarioAdminOut:
        existing = await db.scalar(
            select(Usuario).where(
                Usuario.email == payload.email,
                Usuario.deleted_at.is_(None),
            )
        )
        if existing is not None:
            raise AppException(
                message="Ya existe un usuario con ese correo electrónico",
                status_code=status.HTTP_409_CONFLICT,
            )

        user = Usuario(
            nombre=payload.nombre,
            email=payload.email,
            password_hash=hash_password(payload.password),
            rol=payload.rol,
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return UsuarioAdminOut.model_validate(user)

    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: str,
        payload: UsuarioUpdateRequest,
    ) -> UsuarioAdminOut:
        user = await db.scalar(
            select(Usuario).where(
                Usuario.id == user_id,
                Usuario.deleted_at.is_(None),
            )
        )
        if user is None:
            raise AppException(
                message="Usuario no encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if payload.email is not None and payload.email != user.email:
            conflict = await db.scalar(
                select(Usuario).where(
                    Usuario.email == payload.email,
                    Usuario.deleted_at.is_(None),
                )
            )
            if conflict is not None:
                raise AppException(
                    message="Ya existe un usuario con ese correo electrónico",
                    status_code=status.HTTP_409_CONFLICT,
                )
            user.email = payload.email

        if payload.nombre is not None:
            user.nombre = payload.nombre
        if payload.password is not None:
            user.password_hash = hash_password(payload.password)
        if payload.rol is not None:
            user.rol = payload.rol

        await db.commit()
        await db.refresh(user)
        return UsuarioAdminOut.model_validate(user)

    @staticmethod
    async def delete_user(
        db: AsyncSession,
        user_id: str,
        requesting_user_id: str,
    ) -> None:
        if user_id == requesting_user_id:
            raise AppException(
                message="No puedes eliminar tu propio usuario",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = await db.scalar(
            select(Usuario).where(
                Usuario.id == user_id,
                Usuario.deleted_at.is_(None),
            )
        )
        if user is None:
            raise AppException(
                message="Usuario no encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        from datetime import datetime, timezone
        user.deleted_at = datetime.now(timezone.utc)
        await db.commit()
