from __future__ import annotations

from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.alimentacion.models import AlimentacionRegistro
from app.modules.alimentacion.schemas import (
    AlimentacionCreate,
    AlimentacionOut,
    AlimentacionUpdate,
    ConversionAlimenticiaOut,
)
from app.modules.produccion.models import ProduccionHuevo


REGISTRO_ALIMENTACION_NO_ENCONTRADO = "Registro de alimentacion no encontrado"


class AlimentacionService:
    KG_POR_HUEVO = 0.06

    @staticmethod
    async def list(db: AsyncSession) -> list[AlimentacionOut]:
        result = await db.execute(
            select(AlimentacionRegistro)
            .where(AlimentacionRegistro.deleted_at.is_(None))
            .order_by(AlimentacionRegistro.fecha.desc())
        )
        return [AlimentacionOut.model_validate(item) for item in result.scalars().all()]

    @staticmethod
    async def get_by_id(db: AsyncSession, registro_id: str) -> AlimentacionOut:
        result = await db.execute(
            select(AlimentacionRegistro).where(
                AlimentacionRegistro.id == registro_id,
                AlimentacionRegistro.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise AppException(
                message=REGISTRO_ALIMENTACION_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return AlimentacionOut.model_validate(row)

    @staticmethod
    async def create(db: AsyncSession, payload: AlimentacionCreate) -> AlimentacionOut:
        row = AlimentacionRegistro(**payload.model_dump())
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return AlimentacionOut.model_validate(row)

    @staticmethod
    async def update(
        db: AsyncSession,
        registro_id: str,
        payload: AlimentacionUpdate,
    ) -> AlimentacionOut:
        result = await db.execute(
            select(AlimentacionRegistro).where(
                AlimentacionRegistro.id == registro_id,
                AlimentacionRegistro.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise AppException(
                message=REGISTRO_ALIMENTACION_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, value)

        await db.commit()
        await db.refresh(row)
        return AlimentacionOut.model_validate(row)

    @staticmethod
    async def delete(db: AsyncSession, registro_id: str) -> None:
        result = await db.execute(
            select(AlimentacionRegistro).where(
                AlimentacionRegistro.id == registro_id,
                AlimentacionRegistro.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise AppException(
                message=REGISTRO_ALIMENTACION_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def list_rango(
        db: AsyncSession,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> list[AlimentacionOut]:
        result = await db.execute(
            select(AlimentacionRegistro)
            .where(
                AlimentacionRegistro.deleted_at.is_(None),
                AlimentacionRegistro.fecha >= fecha_inicio,
                AlimentacionRegistro.fecha <= fecha_fin,
            )
            .order_by(AlimentacionRegistro.fecha.desc())
        )
        return [AlimentacionOut.model_validate(item) for item in result.scalars().all()]

    @staticmethod
    async def calcular_conversion_alimenticia(
        db: AsyncSession,
        lote_id: str,
        fecha_inicio: datetime | None = None,
        fecha_fin: datetime | None = None,
    ) -> ConversionAlimenticiaOut:
        filtros_alimento = [
            AlimentacionRegistro.lote_id == lote_id,
            AlimentacionRegistro.deleted_at.is_(None),
        ]
        filtros_produccion = [
            ProduccionHuevo.lote_id == lote_id,
            ProduccionHuevo.deleted_at.is_(None),
        ]

        if fecha_inicio is not None:
            filtros_alimento.append(AlimentacionRegistro.fecha >= fecha_inicio)
            filtros_produccion.append(ProduccionHuevo.fecha >= fecha_inicio)
        if fecha_fin is not None:
            filtros_alimento.append(AlimentacionRegistro.fecha <= fecha_fin)
            filtros_produccion.append(ProduccionHuevo.fecha <= fecha_fin)

        total_alimento = await db.scalar(
            select(
                func.coalesce(func.sum(AlimentacionRegistro.cantidad_kg), 0.0)
            ).where(*filtros_alimento)
        )
        total_huevos = await db.scalar(
            select(func.coalesce(func.sum(ProduccionHuevo.cantidad), 0)).where(
                *filtros_produccion
            )
        )

        kg_alimento = float(total_alimento or 0.0)
        kg_huevo = round(float(total_huevos or 0) * AlimentacionService.KG_POR_HUEVO, 2)
        conversion = round(kg_alimento / kg_huevo, 4) if kg_huevo > 0 else None

        return ConversionAlimenticiaOut(
            lote_id=lote_id,
            kg_alimento=round(kg_alimento, 2),
            kg_huevo=kg_huevo,
            conversion_alimenticia=conversion,
        )
