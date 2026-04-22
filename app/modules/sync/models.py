from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel
from app.shared.enums import EstadoSync


class SyncLog(BaseModel):
    __tablename__ = "sync_logs"

    operacion: Mapped[str] = mapped_column(String(40), nullable=False)
    entidad: Mapped[str] = mapped_column(String(80), nullable=False)
    entidad_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    cliente_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    procesado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    estado: Mapped[EstadoSync] = mapped_column(
        SAEnum(EstadoSync),
        default=EstadoSync.PENDIENTE,
        nullable=False,
        index=True,
    )
    mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
