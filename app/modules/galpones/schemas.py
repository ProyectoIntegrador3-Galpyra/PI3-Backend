from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import EstadoGalpon


class GalponBase(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    ubicacion: str = Field(min_length=1, max_length=200)
    capacidad: int = Field(gt=0)
    estado: EstadoGalpon = EstadoGalpon.ACTIVO
    descripcion: str | None = None


class GalponCreate(GalponBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nombre": "Galpón Norte",
                "ubicacion": "Lebrija, Santander",
                "capacidad": 500,
                "estado": "ACTIVO",
                "descripcion": "Galpón principal",
                "propietario_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )

    propietario_id: str = Field(min_length=36, max_length=36)


class GalponUpdate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {"capacidad": 750, "estado": "MANTENIMIENTO"},
        }
    )

    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    ubicacion: str | None = Field(default=None, min_length=1, max_length=200)
    capacidad: int | None = Field(default=None, gt=0)
    estado: EstadoGalpon | None = None
    descripcion: str | None = None


class GalponOut(GalponBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    propietario_id: str
    created_at: datetime
    updated_at: datetime
