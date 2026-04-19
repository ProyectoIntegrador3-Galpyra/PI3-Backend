from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.core.responses import success_response
from app.modules.auth.models import Usuario
from app.modules.dashboard.service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "",
    summary="Dashboard ejecutivo",
    description="Métricas consolidadas del sistema. Requiere rol ADMIN.",
)
async def get_dashboard(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[Usuario, Depends(require_admin)],
) -> dict:
    data = await DashboardService.get_metrics(db)
    return success_response(message="Métricas del dashboard obtenidas", data=data)
