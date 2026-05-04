from datetime import datetime, timezone

from fastapi import status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.aves.models import LoteAve, MovimientoAve
from app.modules.aves.schemas import (
    HistorialMortalidadOut,
    LoteAveCreate,
    LoteAveOut,
    LoteAveUpdate,
    MovimientoAveCreate,
    MovimientoAveOut,
)
from app.modules.galpones.models import Galpon
from app.shared.enums import TipoMovimientoAve, EstadoLote


LOTE_NO_ENCONTRADO = "Lote no encontrado"


class AvesService:
    @staticmethod
    async def list_lotes(db: AsyncSession) -> list[LoteAveOut]:
        result = await db.execute(
            select(LoteAve)
            .where(LoteAve.deleted_at.is_(None))
            .order_by(LoteAve.created_at.desc())
        )
        return [LoteAveOut.model_validate(item) for item in result.scalars().all()]

    @staticmethod
    async def list_lotes_por_galpon(
        db: AsyncSession,
        galpon_id: str,
    ) -> list[LoteAveOut]:
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
    async def get_lote(db: AsyncSession, lote_id: str) -> LoteAveOut:
        result = await db.execute(
            select(LoteAve).where(LoteAve.id == lote_id, LoteAve.deleted_at.is_(None))
        )
        lote = result.scalar_one_or_none()
        if lote is None:
            raise AppException(
                message=LOTE_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return LoteAveOut.model_validate(lote)

    @staticmethod
    async def create_lote(db: AsyncSession, payload: LoteAveCreate) -> LoteAveOut:
        galpon_result = await db.execute(
            select(Galpon).where(
                Galpon.id == payload.galpon_id,
                Galpon.deleted_at.is_(None),
            )
        )
        galpon = galpon_result.scalar_one_or_none()
        if galpon is None:
            raise AppException(
                message="Galpon no encontrado para crear lote",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if payload.cantidad_inicial > galpon.capacidad:
            raise AppException(
                message="La cantidad inicial supera la capacidad del galpon",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        data = payload.model_dump()
        if data.get("cantidad_actual") is None:
            data["cantidad_actual"] = payload.cantidad_inicial

        if data["cantidad_actual"] > galpon.capacidad:
            raise AppException(
                message="La cantidad actual supera la capacidad del galpon",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Validar que el total de aves en el galpón no supere la capacidad
        aves_existentes_result = await db.execute(
            select(func.sum(LoteAve.cantidad_actual)).where(
                LoteAve.galpon_id == payload.galpon_id,
                LoteAve.deleted_at.is_(None),
                LoteAve.estado == EstadoLote.ACTIVO,
            )
        )
        aves_existentes = aves_existentes_result.scalar() or 0
        total_aves_despues = aves_existentes + data["cantidad_actual"]

        if total_aves_despues > galpon.capacidad:
            espacio_disponible = galpon.capacidad - aves_existentes
            raise AppException(
                message=f"No hay espacio disponible. Aves actuales: {aves_existentes}, "
                        f"Espacio: {espacio_disponible}, Solicitado: {data['cantidad_actual']}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        lote = LoteAve(**data)
        db.add(lote)
        await db.commit()
        await db.refresh(lote)
        return LoteAveOut.model_validate(lote)

    @staticmethod
    async def update_lote(
        db: AsyncSession,
        lote_id: str,
        payload: LoteAveUpdate,
    ) -> LoteAveOut:
        result = await db.execute(
            select(LoteAve).where(LoteAve.id == lote_id, LoteAve.deleted_at.is_(None))
        )
        lote = result.scalar_one_or_none()
        if lote is None:
            raise AppException(
                message=LOTE_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(lote, field, value)

        await db.commit()
        await db.refresh(lote)
        return LoteAveOut.model_validate(lote)

    @staticmethod
    async def delete_lote(db: AsyncSession, lote_id: str) -> None:
        result = await db.execute(
            select(LoteAve).where(LoteAve.id == lote_id, LoteAve.deleted_at.is_(None))
        )
        lote = result.scalar_one_or_none()
        if lote is None:
            raise AppException(
                message=LOTE_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        lote.deleted_at = datetime.now(timezone.utc)
        await db.commit()

    @staticmethod
    async def registrar_movimiento(
        db: AsyncSession,
        payload: MovimientoAveCreate,
        tipo_forzado: TipoMovimientoAve | None = None,
    ) -> MovimientoAveOut:
        result = await db.execute(
            select(LoteAve).where(
                LoteAve.id == payload.lote_id, LoteAve.deleted_at.is_(None)
            )
        )
        lote = result.scalar_one_or_none()
        if lote is None:
            raise AppException(
                message="Lote no encontrado para movimiento",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        tipo_movimiento = tipo_forzado or payload.tipo_movimiento

        if tipo_movimiento == TipoMovimientoAve.MORTALIDAD:
            if lote.cantidad_actual < payload.cantidad:
                raise AppException(
                    message="La mortalidad supera la cantidad actual del lote"
                )
            lote.cantidad_actual -= payload.cantidad
        elif tipo_movimiento == TipoMovimientoAve.INGRESO:
            lote.cantidad_actual += payload.cantidad
        else:
            lote.cantidad_actual += payload.cantidad

        movimiento = MovimientoAve(
            lote_id=payload.lote_id,
            tipo_movimiento=tipo_movimiento,
            cantidad=payload.cantidad,
            causa=payload.causa,
            fecha=payload.fecha,
            observaciones=payload.observaciones,
        )

        db.add(movimiento)
        await db.commit()
        await db.refresh(movimiento)
        return MovimientoAveOut.model_validate(movimiento)

    @staticmethod
    async def historial_mortalidad(
        db: AsyncSession,
        lote_id: str,
        fecha_inicio: datetime | None = None,
        fecha_fin: datetime | None = None,
    ) -> HistorialMortalidadOut:
        lote_result = await db.execute(
            select(LoteAve).where(LoteAve.id == lote_id, LoteAve.deleted_at.is_(None))
        )
        lote = lote_result.scalar_one_or_none()
        if lote is None:
            raise AppException(
                message=LOTE_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        conditions = [
            MovimientoAve.lote_id == lote_id,
            MovimientoAve.tipo_movimiento == TipoMovimientoAve.MORTALIDAD,
            MovimientoAve.deleted_at.is_(None),
        ]
        if fecha_inicio is not None:
            conditions.append(MovimientoAve.fecha >= fecha_inicio)
        if fecha_fin is not None:
            conditions.append(MovimientoAve.fecha <= fecha_fin)

        result = await db.execute(
            select(MovimientoAve)
            .where(*conditions)
            .order_by(MovimientoAve.fecha.desc())
        )
        rows = result.scalars().all()
        registros = [MovimientoAveOut.model_validate(row) for row in rows]

        total_mortalidad = sum(item.cantidad for item in registros)
        tasa = (
            round((total_mortalidad / lote.cantidad_inicial) * 100, 2)
            if lote.cantidad_inicial > 0
            else 0.0
        )

        return HistorialMortalidadOut(
            lote_id=lote_id,
            cantidad_inicial_lote=lote.cantidad_inicial,
            total_mortalidad=total_mortalidad,
            tasa_mortalidad_porcentaje=tasa,
            registros=registros,
        )
