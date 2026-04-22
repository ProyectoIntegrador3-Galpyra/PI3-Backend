import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.aves.models import LoteAve
from app.modules.aves.schemas import LoteAveOut
from app.modules.sanidad.models import EventoSanitario
from app.modules.sanidad.schemas import EventoSanitarioOut
from app.modules.trazabilidad.models import TokenTrazabilidad
from app.modules.trazabilidad.schemas import (
    TokenTrazabilidadCreate,
    TokenTrazabilidadOut,
)


class TrazabilidadService:

    @staticmethod
    async def generar_token(
        db: AsyncSession,
        payload: TokenTrazabilidadCreate,
        usuario_id: str,
    ) -> TokenTrazabilidadOut:
        lote = await db.get(LoteAve, payload.lote_id)
        if not lote or lote.deleted_at:
            raise AppException("Lote no encontrado", 404)

        nuevo_token = TokenTrazabilidad(
            lote_id=payload.lote_id,
            token=str(uuid.uuid4()),
            expira_en=datetime.now(timezone.utc)
            + timedelta(days=payload.dias_vigencia),
            generado_por=usuario_id,
        )
        db.add(nuevo_token)
        await db.commit()
        await db.refresh(nuevo_token)
        return TokenTrazabilidadOut.model_validate(nuevo_token)

    @staticmethod
    async def consultar_por_token(db: AsyncSession, token: str) -> dict:
        result = await db.execute(
            select(TokenTrazabilidad).where(
                TokenTrazabilidad.token == token,
                TokenTrazabilidad.deleted_at.is_(None),
            )
        )
        tk = result.scalar_one_or_none()
        if not tk:
            raise AppException("Token no encontrado", 404)
        expira = tk.expira_en
        if expira.tzinfo is None:
            expira = expira.replace(tzinfo=timezone.utc)
        if expira < datetime.now(timezone.utc):
            raise AppException("Token expirado", 410)

        lote = await db.get(LoteAve, tk.lote_id)
        result_san = await db.execute(
            select(EventoSanitario)
            .where(
                EventoSanitario.lote_id == tk.lote_id,
                EventoSanitario.deleted_at.is_(None),
            )
            .order_by(EventoSanitario.fecha.desc())
        )
        eventos = result_san.scalars().all()

        return {
            "lote": LoteAveOut.model_validate(lote).model_dump(),
            "eventos_sanitarios": [
                EventoSanitarioOut.model_validate(e).model_dump() for e in eventos
            ],
            "expira_en": expira.isoformat(),
        }
