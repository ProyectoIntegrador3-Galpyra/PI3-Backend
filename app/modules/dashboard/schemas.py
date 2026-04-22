from pydantic import BaseModel


class DashboardResponse(BaseModel):
    total_aves_activas: int
    produccion_ultimos_7_dias: int
    tasa_mortalidad_porcentaje: float
    alertas: list[str]
