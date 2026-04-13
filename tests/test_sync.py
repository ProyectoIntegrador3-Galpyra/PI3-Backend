from datetime import datetime, timezone
import struct
import zlib
from uuid import uuid4

import pytest


def _png_bytes(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + chunk_type
            + data
            + struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    pixel = bytes(rgba)
    for _ in range(height):
        raw.append(0)
        for _ in range(width):
            raw.extend(pixel)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
        + chunk(b"IEND", b"")
    )


@pytest.mark.asyncio
async def test_sync_batch(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]

    operacion_produccion_id = str(uuid4())
    operacion_mov_id = str(uuid4())

    payload = {
        "operaciones": [
            {
                "id": str(uuid4()),
                "operacion": "UPSERT",
                "entidad": "produccion_huevos",
                "payload": {
                    "id": operacion_produccion_id,
                    "galpon_id": galpon.id,
                    "lote_id": lote.id,
                    "fecha": datetime.now(timezone.utc).isoformat(),
                    "cantidad": 320,
                    "huevos_rotos": 4,
                    "observaciones": "Sync app movil",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid4()),
                "operacion": "UPSERT",
                "entidad": "movimiento_aves",
                "payload": {
                    "id": operacion_mov_id,
                    "lote_id": lote.id,
                    "tipo_movimiento": "MORTALIDAD",
                    "cantidad": 3,
                    "causa": "Prueba sync",
                    "fecha": datetime.now(timezone.utc).isoformat(),
                    "observaciones": "test",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
    }

    response = await client.post("/api/sync", json=payload, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["procesadas"] == 2
    assert body["data"]["fallidas"] == 0

    logs_response = await client.get("/api/sync/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    logs_body = logs_response.json()
    assert logs_body["success"] is True
    assert len(logs_body["data"]) == 2


@pytest.mark.asyncio
async def test_inventario_foto_basico(client, seeded_galpon_lote, auth_headers):
    lote = seeded_galpon_lote["lote"]
    png_bytes = _png_bytes(1, 1, (255, 0, 0, 255))

    process_response = await client.post(
        "/api/inventario/procesar",
        data={"lote_id": lote.id},
        files={"file": ("inventario.png", png_bytes, "image/png")},
        headers=auth_headers,
    )
    assert process_response.status_code == 200
    process_body = process_response.json()
    assert process_body["success"] is True
    job_id = process_body["data"]["job_id"]
    assert process_body["data"]["request_id"]
    assert process_body["data"]["modo"] in ["mock", "model"]
    assert process_body["data"]["warning"] in [None, "resultado_no_confiable"]

    confirm_response = await client.post(
        "/api/inventario/confirmar",
        json={
            "job_id": job_id,
            "conteo_confirmado": 123,
            "lote_id": lote.id,
        },
        headers=auth_headers,
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["success"] is True

    get_response = await client.get(
        f"/api/inventario/jobs/{job_id}", headers=auth_headers
    )
    assert get_response.status_code == 200
    get_body = get_response.json()
    assert get_body["data"]["conteo_confirmado"] == 123


@pytest.mark.asyncio
async def test_inventario_foto_varia_con_imagenes_distintas(
    client, seeded_galpon_lote, auth_headers
):
    lote = seeded_galpon_lote["lote"]

    primera = _png_bytes(1, 1, (255, 0, 0, 255))
    segunda = _png_bytes(3, 2, (0, 255, 0, 255))

    first_response = await client.post(
        "/api/inventario/procesar",
        data={"lote_id": lote.id},
        files={"file": ("a.png", primera, "image/png")},
        headers=auth_headers,
    )
    second_response = await client.post(
        "/api/inventario/procesar",
        data={"lote_id": lote.id},
        files={"file": ("b.png", segunda, "image/png")},
        headers=auth_headers,
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_body = first_response.json()["data"]
    second_body = second_response.json()["data"]

    assert first_body["modo"] in ["mock", "model"]
    assert second_body["modo"] in ["mock", "model"]
    assert first_body["conteo"] >= 0
    assert second_body["conteo"] >= 0


@pytest.mark.asyncio
async def test_inventario_foto_rechaza_imagen_invalida(
    client, seeded_galpon_lote, auth_headers
):
    lote = seeded_galpon_lote["lote"]

    response = await client.post(
        "/api/inventario/procesar",
        data={"lote_id": lote.id},
        files={"file": ("invalid.bin", b"not-an-image", "application/octet-stream")},
        headers=auth_headers,
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "imagen" in body["message"].lower()


@pytest.mark.asyncio
async def test_sync_entidades_faltantes_y_delete(
    client, seeded_galpon_lote, auth_headers
):
    admin = seeded_galpon_lote["admin"]
    galpon = seeded_galpon_lote["galpon"]
    lote = seeded_galpon_lote["lote"]

    now_iso = datetime.now(timezone.utc).isoformat()
    nuevo_galpon_id = str(uuid4())
    nuevo_lote_id = str(uuid4())
    nuevo_evento_id = str(uuid4())
    nueva_alimentacion_id = str(uuid4())

    payload = {
        "operaciones": [
            {
                "id": str(uuid4()),
                "operacion": "CREATE",
                "entidad": "galpones",
                "payload": {
                    "id": nuevo_galpon_id,
                    "nombre": "Galpon Sync",
                    "ubicacion": "Zona 2",
                    "capacidad": 700,
                    "estado": "ACTIVO",
                    "propietario_id": admin.id,
                    "updated_at": now_iso,
                },
                "created_at": now_iso,
            },
            {
                "id": str(uuid4()),
                "operacion": "CREATE",
                "entidad": "lotes_aves",
                "payload": {
                    "id": nuevo_lote_id,
                    "codigo_lote": "SYNC-LOTE-001",
                    "tipo_ave": "PONEDORA",
                    "raza": "Hy-Line",
                    "cantidad_inicial": 150,
                    "cantidad_actual": 150,
                    "fecha_ingreso": now_iso,
                    "galpon_id": nuevo_galpon_id,
                    "estado": "ACTIVO",
                    "updated_at": now_iso,
                },
                "created_at": now_iso,
            },
            {
                "id": str(uuid4()),
                "operacion": "CREATE",
                "entidad": "eventos_sanitarios",
                "payload": {
                    "id": nuevo_evento_id,
                    "lote_id": lote.id,
                    "galpon_id": galpon.id,
                    "tipo_evento": "DIAGNOSTICO",
                    "descripcion": "Evento sync",
                    "producto": "Suplemento",
                    "dosis": "10ml",
                    "responsable": "Tecnico",
                    "fecha": now_iso,
                    "updated_at": now_iso,
                },
                "created_at": now_iso,
            },
            {
                "id": str(uuid4()),
                "operacion": "CREATE",
                "entidad": "alimentacion_registros",
                "payload": {
                    "id": nueva_alimentacion_id,
                    "galpon_id": galpon.id,
                    "lote_id": lote.id,
                    "fecha": now_iso,
                    "tipo_alimento": "Concentrado",
                    "cantidad_kg": 100.5,
                    "costo": 220000,
                    "updated_at": now_iso,
                },
                "created_at": now_iso,
            },
            {
                "id": str(uuid4()),
                "operacion": "DELETE",
                "entidad": "alimentacion_registros",
                "payload": {
                    "id": nueva_alimentacion_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
    }

    response = await client.post("/api/sync", json=payload, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["procesadas"] == 5
    assert body["data"]["fallidas"] == 0
