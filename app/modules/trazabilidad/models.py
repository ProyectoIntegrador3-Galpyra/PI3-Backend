from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel


class TokenTrazabilidad(BaseModel):
    __tablename__ = "tokens_trazabilidad"

    lote_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lotes_aves.id"),
        nullable=False,
        index=True,
    )
    token: Mapped[str] = mapped_column(
        String(36), unique=True, nullable=False, index=True
    )
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generado_por: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("usuarios.id"),
        nullable=False,
    )

    lote = relationship("LoteAve")
    generador = relationship("Usuario")
