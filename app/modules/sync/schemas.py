from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.shared.enums import EstadoSync


class SyncOperation(BaseModel):
    id: str = Field(min_length=1)
    operacion: Literal["CREATE", "UPDATE", "DELETE", "UPSERT"]
    entidad: Literal[
        "produccion_huevos",
        "produccion",
        "movimiento_aves",
        "movimientos_aves",
        "galpones",
        "galpon",
        "lotes_aves",
        "lote_aves",
        "lotes",
        "eventos_sanitarios",
        "evento_sanitario",
        "alimentacion_registros",
        "alimentacion",
    ]
    payload: dict[str, Any]
    created_at: datetime


class SyncRequest(BaseModel):
    operaciones: list[SyncOperation] = Field(min_length=1)


class SyncOperationResult(BaseModel):
    id: str
    entidad: str
    estado: EstadoSync
    mensaje: str


class SyncResponse(BaseModel):
    procesadas: int
    fallidas: int
    detalles: list[SyncOperationResult]


class SyncLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    operacion: str
    entidad: str
    entidad_id: str
    payload_json: dict[str, Any]
    cliente_created_at: datetime
    procesado_at: datetime | None
    estado: EstadoSync
    mensaje: str | None
    created_at: datetime
