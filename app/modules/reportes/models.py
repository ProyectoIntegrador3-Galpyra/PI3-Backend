from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class ReporteGenerado(BaseModel):
    __tablename__ = "reportes_generados"

    tipo: Mapped[str] = mapped_column(String(80), nullable=False)
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    formato: Mapped[str] = mapped_column(String(20), nullable=False)
    url_archivo: Mapped[str | None] = mapped_column(String(300), nullable=True)
    generado_por: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("usuarios.id"),
        nullable=True,
        index=True,
    )

    generador = relationship("Usuario", back_populates="reportes")
