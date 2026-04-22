from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.shared.enums import EstadoLote, TipoMovimientoAve


class LoteAve(BaseModel):
    __tablename__ = "lotes_aves"

    codigo_lote: Mapped[str] = mapped_column(
        String(80), unique=True, nullable=False, index=True
    )
    tipo_ave: Mapped[str] = mapped_column(String(80), nullable=False)
    raza: Mapped[str] = mapped_column(String(120), nullable=False)
    peso_promedio_ingreso_kg: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    cantidad_inicial: Mapped[int] = mapped_column(Integer, nullable=False)
    cantidad_actual: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_ingreso: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    galpon_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("galpones.id"),
        nullable=False,
        index=True,
    )
    estado: Mapped[EstadoLote] = mapped_column(
        SAEnum(EstadoLote),
        default=EstadoLote.ACTIVO,
        nullable=False,
    )

    galpon = relationship("Galpon", back_populates="lotes")
    movimientos = relationship("MovimientoAve", back_populates="lote")
    producciones = relationship("ProduccionHuevo", back_populates="lote")
    eventos_sanitarios = relationship("EventoSanitario", back_populates="lote")
    alimentaciones = relationship("AlimentacionRegistro", back_populates="lote")
    inventario_jobs = relationship("InventarioFotoJob", back_populates="lote")


class MovimientoAve(BaseModel):
    __tablename__ = "movimientos_aves"

    lote_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("lotes_aves.id"),
        nullable=False,
        index=True,
    )
    tipo_movimiento: Mapped[TipoMovimientoAve] = mapped_column(
        SAEnum(TipoMovimientoAve),
        nullable=False,
    )
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    causa: Mapped[str] = mapped_column(String(120), nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)

    lote = relationship("LoteAve", back_populates="movimientos")
