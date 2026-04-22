from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.alimentacion.models import AlimentacionRegistro
from app.modules.aves.models import LoteAve, MovimientoAve
from app.modules.galpones.models import Galpon
from app.modules.produccion.models import ProduccionHuevo
from app.shared.enums import EstadoGalpon, EstadoLote, TipoMovimientoAve


class DashboardService:

    @staticmethod
    async def get_metrics(db: AsyncSession) -> dict:
        now = datetime.now(timezone.utc)
        inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_anio = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        inicio_hoy = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Aves activas
        aves_activas = await db.scalar(
            select(func.sum(LoteAve.cantidad_actual)).where(
                LoteAve.deleted_at.is_(None),
                LoteAve.estado == EstadoLote.ACTIVO,
            )
        ) or 0

        # Producción hoy
        produccion_hoy = await db.scalar(
            select(func.sum(ProduccionHuevo.cantidad)).where(
                ProduccionHuevo.deleted_at.is_(None),
                ProduccionHuevo.fecha >= inicio_hoy,
            )
        ) or 0

        # Producción este mes
        produccion_mes = await db.scalar(
            select(func.sum(ProduccionHuevo.cantidad)).where(
                ProduccionHuevo.deleted_at.is_(None),
                ProduccionHuevo.fecha >= inicio_mes,
            )
        ) or 0

        # Mortalidad este mes
        mortalidad_mes = await db.scalar(
            select(func.sum(MovimientoAve.cantidad)).where(
                MovimientoAve.deleted_at.is_(None),
                MovimientoAve.tipo_movimiento == TipoMovimientoAve.MORTALIDAD,
                MovimientoAve.fecha >= inicio_mes,
            )
        ) or 0

        # Tasa mortalidad mes = bajas_mes / aves_activas * 100
        tasa_mortalidad_mes = (
            round((mortalidad_mes / aves_activas) * 100, 2) if aves_activas > 0 else 0.0
        )

        # Gasto alimento este mes
        gasto_alimento_mes = await db.scalar(
            select(func.sum(AlimentacionRegistro.costo)).where(
                AlimentacionRegistro.deleted_at.is_(None),
                AlimentacionRegistro.fecha >= inicio_mes,
                AlimentacionRegistro.costo.is_not(None),
            )
        ) or 0.0

        # Gasto alimento este año
        gasto_alimento_anio = await db.scalar(
            select(func.sum(AlimentacionRegistro.costo)).where(
                AlimentacionRegistro.deleted_at.is_(None),
                AlimentacionRegistro.fecha >= inicio_anio,
                AlimentacionRegistro.costo.is_not(None),
            )
        ) or 0.0

        # Galpones activos
        galpones_activos = await db.scalar(
            select(func.count(Galpon.id)).where(
                Galpon.deleted_at.is_(None),
                Galpon.estado == EstadoGalpon.ACTIVO,
            )
        ) or 0

        return {
            "aves_activas": int(aves_activas),
            "produccion_hoy": int(produccion_hoy),
            "produccion_mes": int(produccion_mes),
            "mortalidad_mes": int(mortalidad_mes),
            "tasa_mortalidad_mes": tasa_mortalidad_mes,
            "gasto_alimento_mes": float(gasto_alimento_mes),
            "gasto_alimento_año": float(gasto_alimento_anio),
            "galpones_activos": int(galpones_activos),
        }
