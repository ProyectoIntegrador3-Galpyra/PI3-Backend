from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.shared.enums import TipoEventoSanitario


class EventoSanitario(BaseModel):
    __tablename__ = "eventos_sanitarios"

    lote_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lotes_aves.id"),
        nullable=False,
        index=True,
    )
    galpon_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("galpones.id"),
        nullable=False,
        index=True,
    )
    tipo_evento: Mapped[TipoEventoSanitario] = mapped_column(
        SAEnum(TipoEventoSanitario),
        nullable=False,
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    producto: Mapped[str] = mapped_column(String(180), nullable=False)
    dosis: Mapped[str] = mapped_column(String(120), nullable=False)
    responsable: Mapped[str] = mapped_column(String(120), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    lote = relationship("LoteAve", back_populates="eventos_sanitarios")
    galpon = relationship("Galpon")
