from datetime import datetime, timedelta, timezone

import pytest


PNG_VALIDO = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
    b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
    b"\xd4n\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.mark.asyncio
async def test_alimentacion_router_crud_y_listados(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]
    fecha = datetime.now(timezone.utc)

    create_response = await client.post(
        "/api/alimentacion",
        json={
            "galpon_id": galpon.id,
            "lote_id": lote.id,
            "fecha": fecha.isoformat(),
            "tipo_alimento": "Concentrado",
            "cantidad_kg": 10.5,
            "costo": 25000,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 200
    registro_id = create_response.json()["data"]["id"]

    list_response = await client.get("/api/alimentacion", headers=auth_headers)
    assert list_response.status_code == 200

    rango_response = await client.get(
        "/api/alimentacion/rango",
        params={
            "fecha_inicio": (fecha - timedelta(days=1)).isoformat(),
            "fecha_fin": (fecha + timedelta(days=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert rango_response.status_code == 200

    conversion_response = await client.get(
        f"/api/alimentacion/conversion/{lote.id}",
        params={
            "fecha_inicio": (fecha - timedelta(days=1)).isoformat(),
            "fecha_fin": (fecha + timedelta(days=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert conversion_response.status_code == 200

    get_response = await client.get(
        f"/api/alimentacion/{registro_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200

    update_response = await client.put(
        f"/api/alimentacion/{registro_id}",
        json={"cantidad_kg": 11.0},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    delete_response = await client.delete(
        f"/api/alimentacion/{registro_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_produccion_router_crud_y_listados(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]
    fecha = datetime.now(timezone.utc)

    create_response = await client.post(
        "/api/produccion",
        json={
            "galpon_id": galpon.id,
            "lote_id": lote.id,
            "fecha": fecha.isoformat(),
            "cantidad": 130,
            "huevos_rotos": 2,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 200
    produccion_id = create_response.json()["data"]["id"]

    list_response = await client.get("/api/produccion", headers=auth_headers)
    assert list_response.status_code == 200

    rango_response = await client.get(
        "/api/produccion/rango",
        params={
            "fecha_inicio": (fecha - timedelta(days=1)).isoformat(),
            "fecha_fin": (fecha + timedelta(days=1)).isoformat(),
        },
        headers=auth_headers,
    )
    assert rango_response.status_code == 200

    galpon_response = await client.get(
        f"/api/produccion/galpon/{galpon.id}",
        headers=auth_headers,
    )
    assert galpon_response.status_code == 200

    get_response = await client.get(
        f"/api/produccion/{produccion_id}",
        headers=auth_headers,
    )
    assert get_response.status_code == 200

    update_response = await client.put(
        f"/api/produccion/{produccion_id}",
        json={"cantidad": 140},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    delete_response = await client.delete(
        f"/api/produccion/{produccion_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_aves_router_listas_y_lote_crud(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]

    list_response = await client.get("/api/lotes", headers=auth_headers)
    assert list_response.status_code == 200

    list_por_galpon_response = await client.get(
        f"/api/lotes/galpon/{galpon.id}",
        headers=auth_headers,
    )
    assert list_por_galpon_response.status_code == 200

    get_response = await client.get(f"/api/lotes/{lote.id}", headers=auth_headers)
    assert get_response.status_code == 200

    create_response = await client.post(
        "/api/lotes",
        json={
            "codigo_lote": "L-COV-001",
            "tipo_ave": "PONEDORA",
            "raza": "Hy-Line",
            "cantidad_inicial": 100,
            "cantidad_actual": 100,
            "fecha_ingreso": datetime.now(timezone.utc).isoformat(),
            "galpon_id": galpon.id,
            "estado": "ACTIVO",
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 200
    nuevo_lote_id = create_response.json()["data"]["id"]

    ingreso_response = await client.post(
        "/api/ingresos",
        json={
            "lote_id": nuevo_lote_id,
            "cantidad": 5,
            "causa": "Ajuste de ingreso",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "observaciones": "Prueba cobertura",
        },
        headers=auth_headers,
    )
    assert ingreso_response.status_code == 200

    mortalidad_response = await client.post(
        "/api/mortalidad",
        json={
            "lote_id": nuevo_lote_id,
            "cantidad": 3,
            "causa": "Prueba cobertura mortalidad",
            "fecha": datetime.now(timezone.utc).isoformat(),
            "observaciones": "Prueba",
        },
        headers=auth_headers,
    )
    assert mortalidad_response.status_code == 200

    historial_response = await client.get(
        f"/api/lotes/{nuevo_lote_id}/mortalidad",
        headers=auth_headers,
    )
    assert historial_response.status_code == 200

    update_response = await client.put(
        f"/api/lotes/{nuevo_lote_id}",
        json={"cantidad_actual": 95},
        headers=auth_headers,
    )
    assert update_response.status_code == 200

    delete_response = await client.delete(
        f"/api/lotes/{nuevo_lote_id}",
        headers=auth_headers,
    )
    assert delete_response.status_code == 200


@pytest.mark.asyncio
async def test_inventario_router_jobs_y_confirmacion(client, seeded_galpon_lote, auth_headers):
    lote = seeded_galpon_lote["lote"]
    galpon = seeded_galpon_lote["galpon"]

    procesar_response = await client.post(
        "/api/inventario/procesar",
        data={"lote_id": lote.id},
        files={"file": ("inventario.png", PNG_VALIDO, "image/png")},
        headers=auth_headers,
    )
    assert procesar_response.status_code == 200
    job_id = procesar_response.json()["data"]["job_id"]

    sin_archivo_response = await client.post(
        "/api/inventario/procesar",
        data={"lote_id": lote.id},
        headers=auth_headers,
    )
    assert sin_archivo_response.status_code == 422

    list_jobs_response = await client.get("/api/inventario/jobs", headers=auth_headers)
    assert list_jobs_response.status_code == 200

    get_job_response = await client.get(
        f"/api/inventario/jobs/{job_id}",
        headers=auth_headers,
    )
    assert get_job_response.status_code == 200

    confirmar_response = await client.post(
        "/api/inventario/confirmar",
        json={
            "job_id": job_id,
            "conteo_confirmado": 42,
            "lote_id": lote.id,
            "galpon_id": galpon.id,
        },
        headers=auth_headers,
    )
    assert confirmar_response.status_code == 200
