from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.aves.models import LoteAve
from app.modules.produccion.models import ProduccionHuevo
from app.modules.produccion.schemas import (
    ProduccionCreate,
    ProduccionPromedioOut,
    ProduccionOut,
    ProduccionUpdate,
)


REGISTRO_PRODUCCION_NO_ENCONTRADO = "Registro de produccion no encontrado"


class ProduccionService:
    @staticmethod
    async def _calcular_porcentaje_postura(
        db: AsyncSession,
        lote_id: str | None,
        cantidad_huevos: int,
    ) -> float | None:
        if not lote_id:
            return None

        lote = await db.get(LoteAve, lote_id)
        if lote is None or lote.deleted_at is not None or lote.cantidad_actual <= 0:
            return None

        return round((cantidad_huevos / lote.cantidad_actual) * 100, 2)

    @staticmethod
    async def _validar_fecha_unica_por_lote(
        db: AsyncSession,
        lote_id: str | None,
        fecha: datetime,
        excluyendo_id: str | None = None,
    ) -> None:
        if not lote_id:
            return

        conditions = [
            ProduccionHuevo.lote_id == lote_id,
            ProduccionHuevo.deleted_at.is_(None),
            func.date(ProduccionHuevo.fecha) == fecha.date(),
        ]
        if excluyendo_id is not None:
            conditions.append(ProduccionHuevo.id != excluyendo_id)

        result = await db.execute(select(ProduccionHuevo.id).where(*conditions))
        conflict = result.scalar_one_or_none()
        if conflict is not None:
            raise AppException(
                message="Ya existe un registro de produccion para ese lote en la fecha indicada",
                status_code=status.HTTP_409_CONFLICT,
            )

    @staticmethod
    async def _to_out(db: AsyncSession, row: ProduccionHuevo) -> ProduccionOut:
        data = ProduccionOut.model_validate(row).model_dump()
        data["porcentaje_postura"] = (
            await ProduccionService._calcular_porcentaje_postura(
                db,
                row.lote_id,
                row.cantidad,
            )
        )
        return ProduccionOut.model_validate(data)

    @staticmethod
    async def list(db: AsyncSession) -> list[ProduccionOut]:
        result = await db.execute(
            select(ProduccionHuevo)
            .where(ProduccionHuevo.deleted_at.is_(None))
            .order_by(ProduccionHuevo.fecha.desc())
        )
        items = result.scalars().all()
        return [await ProduccionService._to_out(db, item) for item in items]

    @staticmethod
    async def get_by_id(db: AsyncSession, produccion_id: str) -> ProduccionOut:
        result = await db.execute(
            select(ProduccionHuevo).where(
                ProduccionHuevo.id == produccion_id,
                ProduccionHuevo.deleted_at.is_(None),
            )
        )
        produccion = result.scalar_one_or_none()
        if produccion is None:
            raise AppException(
                message=REGISTRO_PRODUCCION_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return await ProduccionService._to_out(db, produccion)

    @staticmethod
    async def create(db: AsyncSession, payload: ProduccionCreate) -> ProduccionOut:
        await ProduccionService._validar_fecha_unica_por_lote(
            db, payload.lote_id, payload.fecha
        )
        row = ProduccionHuevo(**payload.model_dump())
        db.add(row)
        await db.commit()
        await db.refresh(row)
        return await ProduccionService._to_out(db, row)

    @staticmethod
    async def update(
        db: AsyncSession,
        produccion_id: str,
        payload: ProduccionUpdate,
    ) -> ProduccionOut:
        result = await db.execute(
            select(ProduccionHuevo).where(
                ProduccionHuevo.id == produccion_id,
                ProduccionHuevo.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise AppException(
                message=REGISTRO_PRODUCCION_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        update_data = payload.model_dump(exclude_unset=True)
        lote_id_objetivo = update_data.get("lote_id", row.lote_id)
        fecha_objetivo = update_data.get("fecha", row.fecha)
        await ProduccionService._validar_fecha_unica_por_lote(
            db,
            lote_id_objetivo,
            fecha_objetivo,
            excluyendo_id=row.id,
        )

        for field, value in update_data.items():
            setattr(row, field, value)

        await db.commit()
        await db.refresh(row)
        return await ProduccionService._to_out(db, row)

    @staticmethod
    async def delete(db: AsyncSession, produccion_id: str) -> None:
        result = await db.execute(
            select(ProduccionHuevo).where(
                ProduccionHuevo.id == produccion_id,
                ProduccionHuevo.deleted_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise AppException(
                message=REGISTRO_PRODUCCION_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        row.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def list_rango(
        db: AsyncSession,
        fecha_inicio: datetime,
        fecha_fin: datetime,
    ) -> list[ProduccionOut]:
        result = await db.execute(
            select(ProduccionHuevo)
            .where(
                ProduccionHuevo.deleted_at.is_(None),
                ProduccionHuevo.fecha >= fecha_inicio,
                ProduccionHuevo.fecha <= fecha_fin,
            )
            .order_by(ProduccionHuevo.fecha.desc())
        )
        items = result.scalars().all()
        return [await ProduccionService._to_out(db, item) for item in items]

    @staticmethod
    async def list_por_galpon(db: AsyncSession, galpon_id: str) -> list[ProduccionOut]:
        result = await db.execute(
            select(ProduccionHuevo)
            .where(
                ProduccionHuevo.galpon_id == galpon_id,
                ProduccionHuevo.deleted_at.is_(None),
            )
            .order_by(ProduccionHuevo.fecha.desc())
        )
        items = result.scalars().all()
        return [await ProduccionService._to_out(db, item) for item in items]

    @staticmethod
    async def get_promedios(
        db: AsyncSession,
        lote_id: str,
        periodo: Literal["semanal", "mensual"],
    ) -> list[ProduccionPromedioOut]:
        dialect_name = db.bind.dialect.name if db.bind is not None else ""

        if periodo == "semanal":
            if dialect_name == "sqlite":
                periodo_expr = func.strftime("%Y-W%W", ProduccionHuevo.fecha)
            else:
                periodo_expr = func.date_format(ProduccionHuevo.fecha, "%x-W%v")
        else:
            if dialect_name == "sqlite":
                periodo_expr = func.strftime("%Y-%m", ProduccionHuevo.fecha)
            else:
                periodo_expr = func.date_format(ProduccionHuevo.fecha, "%Y-%m")

        result = await db.execute(
            select(
                periodo_expr.label("periodo"),
                func.sum(ProduccionHuevo.cantidad).label("total_huevos"),
                func.avg(ProduccionHuevo.cantidad).label("promedio_huevos"),
                func.count(ProduccionHuevo.id).label("registros"),
            )
            .where(
                ProduccionHuevo.lote_id == lote_id,
                ProduccionHuevo.deleted_at.is_(None),
            )
            .group_by(periodo_expr)
            .order_by(periodo_expr.desc())
        )

        rows = result.all()
        return [
            ProduccionPromedioOut(
                periodo=str(row.periodo),
                total_huevos=int(row.total_huevos or 0),
                promedio_huevos=round(float(row.promedio_huevos or 0.0), 2),
                registros=int(row.registros or 0),
            )
            for row in rows
        ]
