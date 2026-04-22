from __future__ import annotations

from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.sanidad.models import EventoSanitario
from app.modules.sanidad.schemas import (
    EventoSanitarioCreate,
    EventoSanitarioOut,
    EventoSanitarioUpdate,
)


EVENTO_NO_ENCONTRADO = "Evento sanitario no encontrado"


class SanidadService:
    @staticmethod
    async def list(db: AsyncSession) -> list[EventoSanitarioOut]:
        result = await db.execute(
            select(EventoSanitario)
            .where(EventoSanitario.deleted_at.is_(None))
            .order_by(EventoSanitario.fecha.desc())
        )
        return [
            EventoSanitarioOut.model_validate(item) for item in result.scalars().all()
        ]

    @staticmethod
    async def get_by_id(db: AsyncSession, evento_id: str) -> EventoSanitarioOut:
        result = await db.execute(
            select(EventoSanitario).where(
                EventoSanitario.id == evento_id,
                EventoSanitario.deleted_at.is_(None),
            )
        )
        evento = result.scalar_one_or_none()
        if evento is None:
            raise AppException(
                message=EVENTO_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return EventoSanitarioOut.model_validate(evento)

    @staticmethod
    async def create(
        db: AsyncSession, payload: EventoSanitarioCreate
    ) -> EventoSanitarioOut:
        evento = EventoSanitario(**payload.model_dump())
        db.add(evento)
        await db.commit()
        await db.refresh(evento)
        return EventoSanitarioOut.model_validate(evento)

    @staticmethod
    async def update(
        db: AsyncSession,
        evento_id: str,
        payload: EventoSanitarioUpdate,
    ) -> EventoSanitarioOut:
        result = await db.execute(
            select(EventoSanitario).where(
                EventoSanitario.id == evento_id,
                EventoSanitario.deleted_at.is_(None),
            )
        )
        evento = result.scalar_one_or_none()
        if evento is None:
            raise AppException(
                message=EVENTO_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(evento, field, value)

        await db.commit()
        await db.refresh(evento)
        return EventoSanitarioOut.model_validate(evento)

    @staticmethod
    async def delete(db: AsyncSession, evento_id: str) -> None:
        result = await db.execute(
            select(EventoSanitario).where(
                EventoSanitario.id == evento_id,
                EventoSanitario.deleted_at.is_(None),
            )
        )
        evento = result.scalar_one_or_none()
        if evento is None:
            raise AppException(
                message=EVENTO_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        evento.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def historial_por_lote(
        db: AsyncSession,
        lote_id: str,
    ) -> list[EventoSanitarioOut]:
        result = await db.execute(
            select(EventoSanitario)
            .where(
                EventoSanitario.lote_id == lote_id,
                EventoSanitario.deleted_at.is_(None),
            )
            .order_by(EventoSanitario.fecha.desc())
        )
        return [
            EventoSanitarioOut.model_validate(item) for item in result.scalars().all()
        ]
