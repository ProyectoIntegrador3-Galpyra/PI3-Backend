from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.shared.enums import EstadoGalpon


class Galpon(BaseModel):
    __tablename__ = "galpones"

    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    ubicacion: Mapped[str] = mapped_column(String(200), nullable=False)
    capacidad: Mapped[int] = mapped_column(Integer, nullable=False)
    estado: Mapped[EstadoGalpon] = mapped_column(
        SAEnum(EstadoGalpon),
        default=EstadoGalpon.ACTIVO,
        nullable=False,
    )
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    propietario_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("usuarios.id"),
        nullable=False,
        index=True,
    )

    propietario = relationship("Usuario", back_populates="galpones")
    lotes = relationship("LoteAve", back_populates="galpon")
    producciones = relationship("ProduccionHuevo", back_populates="galpon")
    alimentaciones = relationship("AlimentacionRegistro", back_populates="galpon")
    inventario_jobs = relationship("InventarioFotoJob", back_populates="galpon")
