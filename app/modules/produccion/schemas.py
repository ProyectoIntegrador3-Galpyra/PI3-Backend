from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProduccionBase(BaseModel):
    galpon_id: str = Field(min_length=36, max_length=36)
    lote_id: str | None = Field(default=None, min_length=36, max_length=36)
    fecha: datetime
    cantidad: int = Field(ge=0)
    huevos_yumbo: int = Field(default=0, ge=0)
    huevos_aaa: int = Field(default=0, ge=0)
    huevos_aa: int = Field(default=0, ge=0)
    huevos_a: int = Field(default=0, ge=0)
    huevos_b: int = Field(default=0, ge=0)
    huevos_c: int = Field(default=0, ge=0)
    huevos_rotos: int | None = Field(default=None, ge=0)
    observaciones: str | None = None


class ProduccionCreate(ProduccionBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "galpon_id": "550e8400-e29b-41d4-a716-446655440000",
                "lote_id": "550e8400-e29b-41d4-a716-446655440001",
                "fecha": "2026-03-24T07:00:00Z",
                "cantidad": 280,
                "huevos_rotos": 3,
                "observaciones": "Producción diaria normal",
            }
        }
    )


class ProduccionUpdate(BaseModel):
    galpon_id: str | None = Field(default=None, min_length=36, max_length=36)
    lote_id: str | None = Field(default=None, min_length=36, max_length=36)
    fecha: datetime | None = None
    cantidad: int | None = Field(default=None, ge=0)
    huevos_yumbo: int | None = Field(default=None, ge=0)
    huevos_aaa: int | None = Field(default=None, ge=0)
    huevos_aa: int | None = Field(default=None, ge=0)
    huevos_a: int | None = Field(default=None, ge=0)
    huevos_b: int | None = Field(default=None, ge=0)
    huevos_c: int | None = Field(default=None, ge=0)
    huevos_rotos: int | None = Field(default=None, ge=0)
    observaciones: str | None = None


class ProduccionOut(ProduccionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    porcentaje_postura: float | None = None
    created_at: datetime
    updated_at: datetime


class ProduccionPromedioOut(BaseModel):
    periodo: str
    total_huevos: int
    promedio_huevos: float
    registros: int
