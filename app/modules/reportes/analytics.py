from sqlalchemy import and_, cast, extract, func, select
from sqlalchemy import Integer
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.alimentacion.models import AlimentacionRegistro
from app.modules.aves.models import LoteAve, MovimientoAve
from app.modules.galpones.models import Galpon
from app.shared.enums import EstadoLote, TipoMovimientoAve


def _periodo_label(mes: int | None, año_val: int, mes_val: int, dia_val: int | None = None) -> str:
    """Formatea período como YYYY-MM o YYYY-MM-DD según el nivel de agrupación."""
    if dia_val is not None:
        return f"{año_val:04d}-{mes_val:02d}-{dia_val:02d}"
    return f"{año_val:04d}-{mes_val:02d}"


class ReportesAnalyticsService:

    @staticmethod
    async def produccion(
        db: AsyncSession,
        año: int,
        mes: int | None,
        galpon_id: str | None,
    ) -> list[dict]:
        from app.modules.produccion.models import ProduccionHuevo

        filters = [
            ProduccionHuevo.deleted_at.is_(None),
            cast(extract("year", ProduccionHuevo.fecha), Integer) == año,
        ]
        if mes is not None:
            filters.append(cast(extract("month", ProduccionHuevo.fecha), Integer) == mes)
        if galpon_id is not None:
            filters.append(ProduccionHuevo.galpon_id == galpon_id)

        year_col = cast(extract("year", ProduccionHuevo.fecha), Integer)
        month_col = cast(extract("month", ProduccionHuevo.fecha), Integer)

        if mes is not None:
            day_col = cast(extract("day", ProduccionHuevo.fecha), Integer)
            result = await db.execute(
                select(
                    year_col.label("año"),
                    month_col.label("mes"),
                    day_col.label("dia"),
                    func.sum(ProduccionHuevo.cantidad).label("total_huevos"),
                    func.count(ProduccionHuevo.id).label("registros"),
                )
                .where(and_(*filters))
                .group_by(year_col, month_col, day_col)
                .order_by(year_col, month_col, day_col)
            )
            rows = result.all()
            return [
                {
                    "periodo": _periodo_label(mes, r.año, r.mes, r.dia),
                    "total_huevos": int(r.total_huevos or 0),
                    "promedio_diario": round((r.total_huevos or 0) / max(r.registros, 1), 1),
                }
                for r in rows
            ]
        else:
            result = await db.execute(
                select(
                    year_col.label("año"),
                    month_col.label("mes"),
                    func.sum(ProduccionHuevo.cantidad).label("total_huevos"),
                    func.count(ProduccionHuevo.id).label("registros"),
                )
                .where(and_(*filters))
                .group_by(year_col, month_col)
                .order_by(year_col, month_col)
            )
            rows = result.all()
            return [
                {
                    "periodo": _periodo_label(None, r.año, r.mes),
                    "total_huevos": int(r.total_huevos or 0),
                    "promedio_diario": round((r.total_huevos or 0) / max(r.registros, 1), 1),
                }
                for r in rows
            ]

    @staticmethod
    async def alimentacion(
        db: AsyncSession,
        año: int,
        mes: int | None,
        galpon_id: str | None,
    ) -> list[dict]:
        filters = [
            AlimentacionRegistro.deleted_at.is_(None),
            cast(extract("year", AlimentacionRegistro.fecha), Integer) == año,
        ]
        if mes is not None:
            filters.append(cast(extract("month", AlimentacionRegistro.fecha), Integer) == mes)
        if galpon_id is not None:
            filters.append(AlimentacionRegistro.galpon_id == galpon_id)

        year_col = cast(extract("year", AlimentacionRegistro.fecha), Integer)
        month_col = cast(extract("month", AlimentacionRegistro.fecha), Integer)

        if mes is not None:
            day_col = cast(extract("day", AlimentacionRegistro.fecha), Integer)
            group_cols = [year_col, month_col, day_col, AlimentacionRegistro.tipo_alimento]
            select_cols = [
                year_col.label("año"),
                month_col.label("mes"),
                day_col.label("dia"),
                AlimentacionRegistro.tipo_alimento,
                func.sum(AlimentacionRegistro.cantidad_kg).label("total_kg"),
                func.sum(AlimentacionRegistro.costo).label("costo_total"),
            ]
            order_cols = [year_col, month_col, day_col]
        else:
            group_cols = [year_col, month_col, AlimentacionRegistro.tipo_alimento]
            select_cols = [
                year_col.label("año"),
                month_col.label("mes"),
                AlimentacionRegistro.tipo_alimento,
                func.sum(AlimentacionRegistro.cantidad_kg).label("total_kg"),
                func.sum(AlimentacionRegistro.costo).label("costo_total"),
            ]
            order_cols = [year_col, month_col]

        result = await db.execute(
            select(*select_cols)
            .where(and_(*filters))
            .group_by(*group_cols)
            .order_by(*order_cols)
        )
        rows = result.all()

        output = []
        for r in rows:
            dia = getattr(r, "dia", None)
            output.append(
                {
                    "periodo": _periodo_label(mes, r.año, r.mes, dia),
                    "tipo_alimento": r.tipo_alimento,
                    "total_kg": round(float(r.total_kg or 0), 2),
                    "costo_total": round(float(r.costo_total or 0), 2),
                }
            )
        return output

    @staticmethod
    async def mortalidad(
        db: AsyncSession,
        año: int,
        mes: int | None,
        galpon_id: str | None,
    ) -> list[dict]:
        filters = [
            MovimientoAve.deleted_at.is_(None),
            MovimientoAve.tipo_movimiento == TipoMovimientoAve.MORTALIDAD,
            cast(extract("year", MovimientoAve.fecha), Integer) == año,
        ]
        if mes is not None:
            filters.append(cast(extract("month", MovimientoAve.fecha), Integer) == mes)

        if galpon_id is not None:
            lote_ids_result = await db.execute(
                select(LoteAve.id).where(
                    LoteAve.galpon_id == galpon_id,
                    LoteAve.deleted_at.is_(None),
                )
            )
            lote_ids = lote_ids_result.scalars().all()
            if not lote_ids:
                return []
            filters.append(MovimientoAve.lote_id.in_(lote_ids))

        year_col = cast(extract("year", MovimientoAve.fecha), Integer)
        month_col = cast(extract("month", MovimientoAve.fecha), Integer)

        if mes is not None:
            day_col = cast(extract("day", MovimientoAve.fecha), Integer)
            result = await db.execute(
                select(
                    year_col.label("año"),
                    month_col.label("mes"),
                    day_col.label("dia"),
                    func.sum(MovimientoAve.cantidad).label("total_bajas"),
                )
                .where(and_(*filters))
                .group_by(year_col, month_col, day_col)
                .order_by(year_col, month_col, day_col)
            )
        else:
            result = await db.execute(
                select(
                    year_col.label("año"),
                    month_col.label("mes"),
                    func.sum(MovimientoAve.cantidad).label("total_bajas"),
                )
                .where(and_(*filters))
                .group_by(year_col, month_col)
                .order_by(year_col, month_col)
            )

        rows = result.all()

        total_aves = await db.scalar(
            select(func.sum(LoteAve.cantidad_actual)).where(
                LoteAve.deleted_at.is_(None),
                LoteAve.estado == EstadoLote.ACTIVO,
            )
        ) or 1

        output = []
        for r in rows:
            dia = getattr(r, "dia", None)
            bajas = int(r.total_bajas or 0)
            output.append(
                {
                    "periodo": _periodo_label(mes, r.año, r.mes, dia),
                    "total_bajas": bajas,
                    "tasa_mortalidad": round((bajas / total_aves) * 100, 4),
                }
            )
        return output

    @staticmethod
    async def inventario(
        db: AsyncSession,
        galpon_id: str | None,
    ) -> list[dict]:
        filters_galpon = [Galpon.deleted_at.is_(None)]
        if galpon_id is not None:
            filters_galpon.append(Galpon.id == galpon_id)

        galpones_result = await db.execute(
            select(Galpon).where(and_(*filters_galpon))
        )
        galpones = galpones_result.scalars().all()

        output = []
        for galpon in galpones:
            lotes_result = await db.execute(
                select(LoteAve).where(
                    LoteAve.galpon_id == galpon.id,
                    LoteAve.deleted_at.is_(None),
                    LoteAve.estado == EstadoLote.ACTIVO,
                )
            )
            lotes = lotes_result.scalars().all()

            for lote in lotes:
                bajas = await db.scalar(
                    select(func.sum(MovimientoAve.cantidad)).where(
                        MovimientoAve.lote_id == lote.id,
                        MovimientoAve.deleted_at.is_(None),
                        MovimientoAve.tipo_movimiento == TipoMovimientoAve.MORTALIDAD,
                    )
                ) or 0

                output.append(
                    {
                        "galpon": galpon.nombre,
                        "galpon_id": galpon.id,
                        "lote_activo": lote.codigo_lote,
                        "lote_id": lote.id,
                        "aves_iniciales": lote.cantidad_inicial,
                        "bajas": int(bajas),
                        "aves_actuales": lote.cantidad_actual,
                    }
                )

        return output
