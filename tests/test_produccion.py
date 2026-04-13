from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_porcentaje_postura_automatico(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]

    payload = {
        "galpon_id": galpon.id,
        "lote_id": lote.id,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "cantidad": 120,
        "huevos_rotos": 2,
        "observaciones": "Produccion diaria",
    }

    response = await client.post("/api/produccion", json=payload, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["porcentaje_postura"] == round(120 / 300 * 100, 2)


@pytest.mark.asyncio
async def test_fecha_unica_por_lote(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]
    fecha = datetime.now(timezone.utc).replace(
        hour=8, minute=0, second=0, microsecond=0
    )

    payload = {
        "galpon_id": galpon.id,
        "lote_id": lote.id,
        "fecha": fecha.isoformat(),
        "cantidad": 140,
    }

    first = await client.post("/api/produccion", json=payload, headers=auth_headers)
    assert first.status_code == 200

    second_payload = {
        "galpon_id": galpon.id,
        "lote_id": lote.id,
        "fecha": fecha.replace(hour=12).isoformat(),
        "cantidad": 150,
    }
    second = await client.post(
        "/api/produccion", json=second_payload, headers=auth_headers
    )
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_promedios_produccion_por_periodo(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]
    fecha_base = datetime.now(timezone.utc).replace(
        hour=8, minute=0, second=0, microsecond=0
    )

    payload_1 = {
        "galpon_id": galpon.id,
        "lote_id": lote.id,
        "fecha": fecha_base.isoformat(),
        "cantidad": 100,
    }
    payload_2 = {
        "galpon_id": galpon.id,
        "lote_id": lote.id,
        "fecha": (fecha_base + timedelta(days=7)).isoformat(),
        "cantidad": 200,
    }

    first = await client.post("/api/produccion", json=payload_1, headers=auth_headers)
    second = await client.post(
        "/api/produccion", json=payload_2, headers=auth_headers
    )
    assert first.status_code == 200
    assert second.status_code == 200

    response = await client.get(
        "/api/produccion/promedios",
        params={"lote_id": lote.id, "periodo": "semanal"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert "total_huevos" in body["data"][0]
