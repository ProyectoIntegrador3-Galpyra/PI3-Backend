from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class AlimentacionRegistro(BaseModel):
    __tablename__ = "alimentacion_registros"

    galpon_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("galpones.id"),
        nullable=False,
        index=True,
    )
    lote_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("lotes_aves.id"),
        nullable=True,
        index=True,
    )
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    tipo_alimento: Mapped[str] = mapped_column(String(120), nullable=False)
    cantidad_kg: Mapped[float] = mapped_column(Float, nullable=False)
    costo: Mapped[float | None] = mapped_column(Float, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    galpon = relationship("Galpon", back_populates="alimentaciones")
    lote = relationship("LoteAve", back_populates="alimentaciones")
