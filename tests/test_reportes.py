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


@pytest.mark.asyncio
async def test_descargar_reporte_requiere_jwt(client):
    response = await client.get("/api/reportes/invalid-id/descargar")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_descargar_reporte_no_encontrado(client, auth_headers):
    response = await client.get(
        "/api/reportes/invalid-reporte-id/descargar",
        headers=auth_headers,
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "no encontrado" in body["message"].lower()


@pytest.mark.asyncio
async def test_descargar_reporte_sin_s3_configurado(client, auth_headers, seeded_admin):
    # Generar un reporte
    payload = {
        "tipo": "inventario",
        "fecha_inicio": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        "fecha_fin": datetime.now(timezone.utc).isoformat(),
        "formato": "PDF",
        "generado_por": seeded_admin.id,
    }
    gen_response = await client.post(
        "/api/reportes/generar",
        json=payload,
        headers=auth_headers,
    )
    reporte_id = gen_response.json()["data"]["id"]

    # Intentar descargar (S3 no está configurado en test)
    response = await client.get(
        f"/api/reportes/{reporte_id}/descargar",
        headers=auth_headers,
    )
    # Esperamos 503 cuando S3 no está disponible
    assert response.status_code == 503
    assert response.json()["success"] is False
