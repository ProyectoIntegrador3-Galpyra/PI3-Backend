from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_conversion_alimenticia(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]
    fecha = datetime.now(timezone.utc).isoformat()

    prod_response = await client.post(
        "/api/produccion",
        json={
            "galpon_id": galpon.id,
            "lote_id": lote.id,
            "fecha": fecha,
            "cantidad": 100,
        },
        headers=auth_headers,
    )
    assert prod_response.status_code == 200

    alim_response = await client.post(
        "/api/alimentacion",
        json={
            "galpon_id": galpon.id,
            "lote_id": lote.id,
            "fecha": fecha,
            "tipo_alimento": "Concentrado",
            "cantidad_kg": 18,
            "costo": 50000,
        },
        headers=auth_headers,
    )
    assert alim_response.status_code == 200

    conversion_response = await client.get(
        f"/api/alimentacion/conversion/{lote.id}",
        headers=auth_headers,
    )
    assert conversion_response.status_code == 200

    data = conversion_response.json()["data"]
    assert data["kg_alimento"] == pytest.approx(18.0)
    assert data["kg_huevo"] == pytest.approx(6.0)
    assert data["conversion_alimenticia"] == pytest.approx(3.0)
