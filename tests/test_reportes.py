from datetime import datetime, timedelta, timezone

import pytest


@pytest.mark.asyncio
async def test_generar_reporte_expone_url_reporte(client, auth_headers):
    payload = {
        "tipo": "produccion",
        "fecha_inicio": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
        "fecha_fin": datetime.now(timezone.utc).isoformat(),
        "formato": "pdf",
    }

    response = await client.post(
        "/api/reportes/generar",
        json=payload,
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["url_reporte"]


@pytest.mark.asyncio
async def test_listar_reportes_incluye_url_reporte(client, auth_headers):
    payload = {
        "tipo": "sanidad",
        "fecha_inicio": (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(),
        "fecha_fin": datetime.now(timezone.utc).isoformat(),
        "formato": "PDF",
    }
    await client.post("/api/reportes/generar", json=payload, headers=auth_headers)

    response = await client.get("/api/reportes", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert "url_reporte" in body["data"][0]
