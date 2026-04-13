from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import EstadoLote, TipoMovimientoAve


class LoteAveBase(BaseModel):
    codigo_lote: str = Field(min_length=1, max_length=80)
    tipo_ave: str = Field(min_length=1, max_length=80)
    raza: str = Field(min_length=1, max_length=120)
    peso_promedio_ingreso_kg: float | None = Field(default=None, ge=0, le=99.99)
    cantidad_inicial: int = Field(gt=0)
    fecha_ingreso: datetime
    galpon_id: str = Field(min_length=36, max_length=36)
    estado: EstadoLote = EstadoLote.ACTIVO


class LoteAveCreate(LoteAveBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "codigo_lote": "L-2026-001",
                "tipo_ave": "PONEDORA",
                "raza": "Hy-Line",
                "cantidad_inicial": 300,
                "fecha_ingreso": "2026-03-24T08:00:00Z",
                "galpon_id": "550e8400-e29b-41d4-a716-446655440000",
                "estado": "ACTIVO",
                "cantidad_actual": 300,
            }
        }
    )

    cantidad_actual: int | None = Field(default=None, ge=0)


class LoteAveUpdate(BaseModel):
    tipo_ave: str | None = Field(default=None, min_length=1, max_length=80)
    raza: str | None = Field(default=None, min_length=1, max_length=120)
    peso_promedio_ingreso_kg: float | None = Field(default=None, ge=0, le=99.99)
    cantidad_actual: int | None = Field(default=None, ge=0)
    estado: EstadoLote | None = None


class LoteAveOut(LoteAveBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cantidad_actual: int
    created_at: datetime
    updated_at: datetime


class MovimientoAveBase(BaseModel):
    lote_id: str = Field(min_length=36, max_length=36)
    cantidad: int = Field(gt=0)
    causa: str = Field(min_length=1, max_length=120)
    fecha: datetime
    observaciones: str | None = None


class MovimientoAveCreate(MovimientoAveBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lote_id": "550e8400-e29b-41d4-a716-446655440000",
                "tipo_movimiento": "MORTALIDAD",
                "cantidad": 5,
                "causa": "Enfermedad respiratoria",
                "fecha": "2026-03-24T10:00:00Z",
                "observaciones": "Aislamiento del lote afectado",
            }
        }
    )

    tipo_movimiento: TipoMovimientoAve = TipoMovimientoAve.AJUSTE


class MovimientoIngresoCreate(MovimientoAveBase):
    pass


class MovimientoMortalidadCreate(MovimientoAveBase):
    pass


class MovimientoAveOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lote_id: str
    tipo_movimiento: TipoMovimientoAve
    cantidad: int
    causa: str
    fecha: datetime
    observaciones: str | None
    created_at: datetime
    updated_at: datetime


class HistorialMortalidadOut(BaseModel):
    lote_id: str
    cantidad_inicial_lote: int
    total_mortalidad: int
    tasa_mortalidad_porcentaje: float
    registros: list[MovimientoAveOut]
