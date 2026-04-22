from __future__ import annotations

from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.aves.models import LoteAve
from app.modules.aves.schemas import LoteAveOut
from app.core.exceptions import AppException
from app.modules.galpones.models import Galpon
from app.modules.galpones.schemas import GalponCreate, GalponOut, GalponUpdate
from app.shared.enums import EstadoLote


GALPON_NO_ENCONTRADO = "Galpon no encontrado"


class GalponService:
    @staticmethod
    async def list(db: AsyncSession) -> list[GalponOut]:
        result = await db.execute(
            select(Galpon)
            .where(Galpon.deleted_at.is_(None))
            .order_by(Galpon.created_at.desc())
        )
        return [GalponOut.model_validate(item) for item in result.scalars().all()]

    @staticmethod
    async def get_by_id(db: AsyncSession, galpon_id: str) -> GalponOut:
        result = await db.execute(
            select(Galpon).where(Galpon.id == galpon_id, Galpon.deleted_at.is_(None))
        )
        galpon = result.scalar_one_or_none()
        if galpon is None:
            raise AppException(
                message=GALPON_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return GalponOut.model_validate(galpon)

    @staticmethod
    async def list_lotes_by_galpon(db: AsyncSession, galpon_id: str) -> list[LoteAveOut]:
        galpon_result = await db.execute(
            select(Galpon).where(Galpon.id == galpon_id, Galpon.deleted_at.is_(None))
        )
        galpon = galpon_result.scalar_one_or_none()
        if galpon is None:
            raise AppException(
                message=GALPON_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        result = await db.execute(
            select(LoteAve)
            .where(
                LoteAve.galpon_id == galpon_id,
                LoteAve.deleted_at.is_(None),
            )
            .order_by(LoteAve.created_at.desc())
        )
        return [LoteAveOut.model_validate(item) for item in result.scalars().all()]

    @staticmethod
    async def create(db: AsyncSession, payload: GalponCreate) -> GalponOut:
        galpon = Galpon(**payload.model_dump())
        db.add(galpon)
        await db.commit()
        await db.refresh(galpon)
        return GalponOut.model_validate(galpon)

    @staticmethod
    async def update(
        db: AsyncSession,
        galpon_id: str,
        payload: GalponUpdate,
    ) -> GalponOut:
        result = await db.execute(
            select(Galpon).where(Galpon.id == galpon_id, Galpon.deleted_at.is_(None))
        )
        galpon = result.scalar_one_or_none()
        if galpon is None:
            raise AppException(
                message=GALPON_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(galpon, field, value)

        await db.commit()
        await db.refresh(galpon)
        return GalponOut.model_validate(galpon)

    @staticmethod
    async def delete(db: AsyncSession, galpon_id: str) -> None:
        result = await db.execute(
            select(Galpon).where(Galpon.id == galpon_id, Galpon.deleted_at.is_(None))
        )
        galpon = result.scalar_one_or_none()
        if galpon is None:
            raise AppException(
                message=GALPON_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        active_lote_result = await db.execute(
            select(LoteAve.id).where(
                LoteAve.galpon_id == galpon_id,
                LoteAve.deleted_at.is_(None),
                LoteAve.estado == EstadoLote.ACTIVO,
            )
        )
        active_lote_id = active_lote_result.scalar_one_or_none()
        if active_lote_id is not None:
            raise AppException(
                message="No se puede eliminar el galpon porque tiene lotes activos",
                status_code=status.HTTP_409_CONFLICT,
            )

        galpon.deleted_at = datetime.now(timezone.utc)
        await db.commit()
