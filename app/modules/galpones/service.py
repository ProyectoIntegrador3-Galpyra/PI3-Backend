from __future__ import annotations

from datetime import datetime, timezone, date, timedelta

from fastapi import status
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.aves.models import LoteAve
from app.modules.aves.schemas import LoteAveOut
from app.core.exceptions import AppException
from app.modules.galpones.models import Galpon, GalponTurno
from app.modules.galpones.schemas import (
    GalponCreate,
    GalponOut,
    GalponUpdate,
    TurnoActivoAssign,
    TurnoActivoResponse,
    TurnoHistorialItem,
)
from app.shared.enums import EstadoLote, RolUsuario, Turno
from app.modules.auth.models import Usuario


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

    @staticmethod
    def _get_turno_actual() -> tuple[Turno, str]:
        """
        Calcula el turno actual según la hora UTC-5 (Colombia).
        Retorna (Turno, hora_inicio_como_string)
        """
        # Crear zona horaria UTC-5
        import pytz
        tz_colombia = pytz.timezone("America/Bogota")
        now_colombia = datetime.now(tz_colombia)
        hour = now_colombia.hour

        if 6 <= hour < 14:
            return Turno.MAÑANA, "06:00"
        elif 14 <= hour < 22:
            return Turno.TARDE, "14:00"
        else:
            return Turno.NOCHE, "22:00"

    @staticmethod
    async def get_turno_activo(
        db: AsyncSession,
        galpon_id: str,
    ) -> TurnoActivoResponse | None:
        """Obtiene la asignación de operario para el turno actual."""
        # Verificar que el galpón existe
        galpon_result = await db.execute(
            select(Galpon).where(Galpon.id == galpon_id, Galpon.deleted_at.is_(None))
        )
        if galpon_result.scalar_one_or_none() is None:
            raise AppException(
                message=GALPON_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        turno_actual, hora_inicio = GalponService._get_turno_actual()
        hoy = date.today()

        # Buscar asignación para hoy y el turno actual
        result = await db.execute(
            select(GalponTurno, Usuario).where(
                GalponTurno.galpon_id == galpon_id,
                GalponTurno.turno == turno_actual,
                GalponTurno.fecha == hoy,
                GalponTurno.activo.is_(True),
                Usuario.id == GalponTurno.usuario_id,
            )
        )
        row = result.first()

        if row is None:
            return TurnoActivoResponse(
                turno=turno_actual,
                operario_nombre=None,
                operario_id=None,
                desde=None,
                mensaje="Sin operario asignado",
            )

        turno_row, usuario_row = row
        return TurnoActivoResponse(
            turno=turno_actual,
            operario_id=usuario_row.id,
            operario_nombre=usuario_row.nombre,
            desde=hora_inicio,
        )

    @staticmethod
    async def assign_turno(
        db: AsyncSession,
        galpon_id: str,
        payload: TurnoActivoAssign,
        current_user: Usuario,
    ) -> None:
        """Asigna un operario a un turno (solo ADMIN)."""
        if current_user.rol != RolUsuario.ADMIN:
            raise AppException(
                message="Solo ADMIN puede asignar turnos",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # Verificar que el galpón existe
        galpon_result = await db.execute(
            select(Galpon).where(Galpon.id == galpon_id, Galpon.deleted_at.is_(None))
        )
        if galpon_result.scalar_one_or_none() is None:
            raise AppException(
                message=GALPON_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Verificar que el usuario existe
        usuario_result = await db.execute(
            select(Usuario).where(
                Usuario.id == payload.usuario_id,
                Usuario.deleted_at.is_(None),
                Usuario.is_active.is_(True),
            )
        )
        if usuario_result.scalar_one_or_none() is None:
            raise AppException(
                message="Usuario no encontrado o inactivo",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # Desactivar asignaciones previas para ese galpón y turno en esa fecha
        await db.execute(
            select(GalponTurno).where(
                GalponTurno.galpon_id == galpon_id,
                GalponTurno.turno == payload.turno,
                GalponTurno.fecha == payload.fecha,
            )
        )

        # Crear nueva asignación
        turno = GalponTurno(
            galpon_id=galpon_id,
            usuario_id=payload.usuario_id,
            turno=payload.turno,
            fecha=payload.fecha,
            activo=True,
        )
        db.add(turno)
        await db.commit()

    @staticmethod
    async def get_turnos_historial(
        db: AsyncSession,
        galpon_id: str,
        limit: int = 30,
    ) -> list[TurnoHistorialItem]:
        """Obtiene el historial de asignaciones de turno para trazabilidad."""
        # Verificar que el galpón existe
        galpon_result = await db.execute(
            select(Galpon).where(Galpon.id == galpon_id, Galpon.deleted_at.is_(None))
        )
        if galpon_result.scalar_one_or_none() is None:
            raise AppException(
                message=GALPON_NO_ENCONTRADO,
                status_code=status.HTTP_404_NOT_FOUND,
            )

        result = await db.execute(
            select(GalponTurno, Usuario)
            .where(
                GalponTurno.galpon_id == galpon_id,
                Usuario.id == GalponTurno.usuario_id,
            )
            .order_by(desc(GalponTurno.created_at))
            .limit(limit)
        )
        items = []
        for turno_row, usuario_row in result.all():
            items.append(
                TurnoHistorialItem(
                    id=turno_row.id,
                    turno=turno_row.turno,
                    operario_id=usuario_row.id,
                    operario_nombre=usuario_row.nombre,
                    fecha=turno_row.fecha,
                    activo=turno_row.activo,
                    created_at=turno_row.created_at,
                )
            )
        return items
