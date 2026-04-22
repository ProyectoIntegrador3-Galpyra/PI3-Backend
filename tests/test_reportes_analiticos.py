from datetime import datetime, timezone

import pytest
import pytest_asyncio
from tests.conftest import TestSessionLocal

from app.modules.alimentacion.models import AlimentacionRegistro
from app.modules.aves.models import MovimientoAve
from app.modules.produccion.models import ProduccionHuevo
from app.shared.enums import TipoMovimientoAve


@pytest_asyncio.fixture
async def datos_analiticos(seeded_galpon_lote):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]
    ahora = datetime.now(timezone.utc)

    async with TestSessionLocal() as session:
        prod = ProduccionHuevo(
            galpon_id=galpon.id,
            lote_id=lote.id,
            fecha=ahora,
            cantidad=500,
        )
        ali = AlimentacionRegistro(
            galpon_id=galpon.id,
            lote_id=lote.id,
            fecha=ahora,
            tipo_alimento="Balanceado A",
            cantidad_kg=30.0,
            costo=150000,
        )
        mov = MovimientoAve(
            lote_id=lote.id,
            tipo_movimiento=TipoMovimientoAve.MORTALIDAD,
            cantidad=5,
            causa="Natural",
            fecha=ahora,
        )
        session.add_all([prod, ali, mov])
        await session.commit()

    return {"galpon": galpon, "lote": lote, "anio": ahora.year, "mes": ahora.month}


# ─── GET /api/reportes/produccion ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reporte_produccion_ok(client, auth_headers, datos_analiticos):
    anio = datos_analiticos["anio"]
    response = await client.get(
        f"/api/reportes/produccion?anio={anio}", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert "total_huevos" in body["data"][0]
    assert "promedio_diario" in body["data"][0]


@pytest.mark.asyncio
async def test_reporte_produccion_con_mes(client, auth_headers, datos_analiticos):
    anio = datos_analiticos["anio"]
    mes = datos_analiticos["mes"]
    response = await client.get(
        f"/api/reportes/produccion?anio={anio}&mes={mes}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_reporte_produccion_requiere_admin(client, seeded_galpon_lote):
    response = await client.get("/api/reportes/produccion?anio=2026")
    assert response.status_code == 401


# ─── GET /api/reportes/alimentacion ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_reporte_alimentacion_ok(client, auth_headers, datos_analiticos):
    anio = datos_analiticos["anio"]
    response = await client.get(
        f"/api/reportes/alimentacion?anio={anio}", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert "total_kg" in body["data"][0]
    assert "costo_total" in body["data"][0]


@pytest.mark.asyncio
async def test_reporte_alimentacion_con_mes(client, auth_headers, datos_analiticos):
    anio = datos_analiticos["anio"]
    mes = datos_analiticos["mes"]
    response = await client.get(
        f"/api/reportes/alimentacion?anio={anio}&mes={mes}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


# ─── GET /api/reportes/mortalidad ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reporte_mortalidad_ok(client, auth_headers, datos_analiticos):
    anio = datos_analiticos["anio"]
    response = await client.get(
        f"/api/reportes/mortalidad?anio={anio}", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert "total_bajas" in body["data"][0]
    assert "tasa_mortalidad" in body["data"][0]


@pytest.mark.asyncio
async def test_reporte_mortalidad_con_mes(client, auth_headers, datos_analiticos):
    anio = datos_analiticos["anio"]
    mes = datos_analiticos["mes"]
    response = await client.get(
        f"/api/reportes/mortalidad?anio={anio}&mes={mes}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_reporte_mortalidad_filtro_galpon(client, auth_headers, datos_analiticos):
    anio = datos_analiticos["anio"]
    galpon_id = datos_analiticos["galpon"].id
    response = await client.get(
        f"/api/reportes/mortalidad?anio={anio}&galpon_id={galpon_id}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_reporte_mortalidad_galpon_sin_lotes(client, auth_headers):
    response = await client.get(
        "/api/reportes/mortalidad?anio=2020&galpon_id=galpon-inexistente",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"] == []


# ─── GET /api/reportes/inventario ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reporte_inventario_ok(client, auth_headers, seeded_galpon_lote):
    response = await client.get("/api/reportes/inventario", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    row = body["data"][0]
    assert "galpon" in row
    assert "lote_activo" in row
    assert "aves_iniciales" in row
    assert "aves_actuales" in row


@pytest.mark.asyncio
async def test_reporte_inventario_filtro_galpon(client, auth_headers, seeded_galpon_lote):
    galpon_id = seeded_galpon_lote["galpon"].id
    response = await client.get(
        f"/api/reportes/inventario?galpon_id={galpon_id}", headers=auth_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert all(r["galpon_id"] == galpon_id for r in body["data"])


# ─── GET /api/dashboard ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dashboard_ok(client, auth_headers, seeded_galpon_lote):
    response = await client.get("/api/dashboard", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    for campo in [
        "aves_activas",
        "produccion_hoy",
        "produccion_mes",
        "mortalidad_mes",
        "tasa_mortalidad_mes",
        "gasto_alimento_mes",
        "gasto_alimento_año",
        "galpones_activos",
    ]:
        assert campo in data, f"Campo faltante en dashboard: {campo}"


@pytest.mark.asyncio
async def test_dashboard_requiere_admin(client, seeded_galpon_lote):
    response = await client.get("/api/dashboard")
    assert response.status_code == 401
