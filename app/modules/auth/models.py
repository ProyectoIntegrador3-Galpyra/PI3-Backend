from datetime import datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel
from app.shared.enums import RolUsuario


class Usuario(BaseModel):
    __tablename__ = "usuarios"

    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(
        String(180), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[RolUsuario] = mapped_column(
        SAEnum(RolUsuario),
        default=RolUsuario.PRODUCTOR,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="usuario",
        cascade="all, delete-orphan",
    )
    galpones = relationship("Galpon", back_populates="propietario")
    reportes = relationship("ReporteGenerado", back_populates="generador")


class RefreshToken(BaseModel):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("usuarios.id"),
        index=True,
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    usuario = relationship("Usuario", back_populates="refresh_tokens")
