from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shared.enums import EstadoInventarioFoto


class InventarioProcesarResponse(BaseModel):
    conteo: int | None
    bounding_boxes: list[dict[str, Any]]
    job_id: str
    modo: str
    source: str
    request_id: str
    warning: str | None = None


class InventarioConfirmarRequest(BaseModel):
    job_id: str = Field(min_length=36, max_length=36)
    conteo_confirmado: int = Field(ge=0)
    lote_id: str | None = Field(default=None, min_length=36, max_length=36)
    galpon_id: str | None = Field(default=None, min_length=36, max_length=36)

    @model_validator(mode="after")
    def validate_scope(self) -> "InventarioConfirmarRequest":
        if self.lote_id is None and self.galpon_id is None:
            raise ValueError("Debe enviar lote_id o galpon_id")
        return self


class ConfirmarInventarioResponse(BaseModel):
    confirmado: bool = True
    lote_id: str
    cantidad_confirmada: int
    job_id: str


class InventarioFotoJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lote_id: str | None
    galpon_id: str | None
    image_url: str | None
    filename: str | None
    conteo_estimado: int | None
    conteo_confirmado: int | None
    origen: str
    estado: EstadoInventarioFoto
    bounding_boxes_json: list[dict[str, Any]] | None
    procesado_en: datetime | None
    confirmado_en: datetime | None
    created_at: datetime
    updated_at: datetime
