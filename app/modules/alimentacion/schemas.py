from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AlimentacionBase(BaseModel):
    galpon_id: str = Field(min_length=36, max_length=36)
    lote_id: str | None = Field(default=None, min_length=36, max_length=36)
    fecha: datetime
    tipo_alimento: str = Field(min_length=1, max_length=120)
    cantidad_kg: float = Field(gt=0)
    costo: float | None = Field(default=None, ge=0)
    observaciones: str | None = None


class AlimentacionCreate(AlimentacionBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "galpon_id": "550e8400-e29b-41d4-a716-446655440000",
                "lote_id": "550e8400-e29b-41d4-a716-446655440001",
                "fecha": "2026-03-24T06:30:00Z",
                "tipo_alimento": "Concentrado",
                "cantidad_kg": 20.5,
                "costo": 65000,
                "observaciones": "Suministro matutino",
            }
        }
    )


class AlimentacionUpdate(BaseModel):
    fecha: datetime | None = None
    tipo_alimento: str | None = Field(default=None, min_length=1, max_length=120)
    cantidad_kg: float | None = Field(default=None, gt=0)
    costo: float | None = Field(default=None, ge=0)
    observaciones: str | None = None


class AlimentacionOut(AlimentacionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    updated_at: datetime


class ConversionAlimenticiaOut(BaseModel):
    lote_id: str
    kg_alimento: float
    kg_huevo: float
    conversion_alimenticia: float | None
