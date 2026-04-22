from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.shared.enums import EstadoInventarioFoto


class InventarioFotoJob(BaseModel):
    __tablename__ = "inventario_foto_jobs"

    lote_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("lotes_aves.id"),
        nullable=True,
        index=True,
    )
    galpon_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("galpones.id"),
        nullable=True,
        index=True,
    )
    image_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    conteo_estimado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conteo_confirmado: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origen: Mapped[str] = mapped_column(String(30), default="cloud", nullable=False)
    estado: Mapped[EstadoInventarioFoto] = mapped_column(
        SAEnum(EstadoInventarioFoto),
        default=EstadoInventarioFoto.PENDIENTE,
        nullable=False,
    )
    bounding_boxes_json: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    procesado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    confirmado_en: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    lote = relationship("LoteAve", back_populates="inventario_jobs")
    galpon = relationship("Galpon", back_populates="inventario_jobs")
