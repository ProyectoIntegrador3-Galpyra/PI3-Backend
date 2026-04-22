from datetime import datetime, timezone

import pytest

from app.modules.aves.models import MovimientoAve
from app.modules.produccion.models import ProduccionHuevo
from app.shared.enums import TipoMovimientoAve
from tests.conftest import TestSessionLocal

CAMPOS_DASHBOARD = [
    "aves_activas",
    "produccion_hoy",
    "produccion_mes",
    "mortalidad_mes",
    "tasa_mortalidad_mes",
    "gasto_alimento_mes",
    "gasto_alimento_año",
    "galpones_activos",
]


@pytest.mark.asyncio
async def test_dashboard_vacio(client, auth_headers):
    response = await client.get("/api/dashboard", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    for campo in CAMPOS_DASHBOARD:
        assert campo in data, f"Campo faltante: {campo}"
    assert data["aves_activas"] == 0
    assert data["produccion_hoy"] == 0
    assert data["tasa_mortalidad_mes"] == pytest.approx(0.0)
    assert data["galpones_activos"] == 0


@pytest.mark.asyncio
async def test_dashboard_con_datos(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]

    async with TestSessionLocal() as session:
        produccion = ProduccionHuevo(
            galpon_id=galpon.id,
            lote_id=lote.id,
            fecha=datetime.now(timezone.utc),
            cantidad=250,
            huevos_rotos=5,
        )
        mortalidad = MovimientoAve(
            lote_id=lote.id,
            tipo_movimiento=TipoMovimientoAve.MORTALIDAD,
            cantidad=10,
            causa="Enfermedad",
            fecha=datetime.now(timezone.utc),
        )
        session.add_all([produccion, mortalidad])
        await session.commit()

    response = await client.get("/api/dashboard", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]

    assert data["aves_activas"] == 300
    assert data["produccion_hoy"] == 250
    assert data["produccion_mes"] == 250
    assert data["mortalidad_mes"] == 10
    # tasa: 10 / 300 * 100 = 3.33
    assert data["tasa_mortalidad_mes"] == pytest.approx(round(10 / 300 * 100, 2))
    assert data["galpones_activos"] == 1
