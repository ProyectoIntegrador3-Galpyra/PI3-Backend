from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TokenTrazabilidadCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "lote_id": "550e8400-e29b-41d4-a716-446655440000",
                "dias_vigencia": 30,
            }
        }
    )

    lote_id: str = Field(min_length=36, max_length=36)
    dias_vigencia: int = Field(default=30, ge=1)


class TokenTrazabilidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    token: str
    lote_id: str
    expira_en: datetime


class TrazabilidadPublicaOut(BaseModel):
    lote: dict
    eventos_sanitarios: list[dict]
    expira_en: datetime
