from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReporteBase(BaseModel):
    tipo: str = Field(min_length=1, max_length=80)
    fecha_inicio: datetime
    fecha_fin: datetime
    formato: Literal["PDF"]
    url_archivo: str | None = None
    generado_por: str | None = Field(default=None, min_length=36, max_length=36)


class ReporteGenerarRequest(BaseModel):
    tipo: str = Field(min_length=1, max_length=80)
    fecha_inicio: datetime
    fecha_fin: datetime
    formato: Literal["PDF"]
    generado_por: str | None = Field(default=None, min_length=36, max_length=36)

    @field_validator("formato", mode="before")
    @classmethod
    def normalize_formato(cls, value: str) -> str:
        return str(value).upper()


class ReporteOut(ReporteBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
