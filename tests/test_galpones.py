import pytest


@pytest.mark.asyncio
async def test_crud_galpones(client, seeded_admin, auth_headers):
    create_response = await client.post(
        "/api/galpones",
        json={
            "nombre": "Galpon Integracion",
            "ubicacion": "Lebrija, Santander",
            "capacidad": 700,
            "estado": "ACTIVO",
            "descripcion": "Prueba CRUD",
            "propietario_id": seeded_admin.id,
        },
        headers=auth_headers,
    )
    assert create_response.status_code == 200
    create_body = create_response.json()
    assert create_body["success"] is True
    galpon_id = create_body["data"]["id"]

    list_response = await client.get("/api/galpones", headers=auth_headers)
    assert list_response.status_code == 200
    assert len(list_response.json()["data"]) == 1

    update_response = await client.put(
        f"/api/galpones/{galpon_id}",
        json={"capacidad": 750, "estado": "MANTENIMIENTO"},
        headers=auth_headers,
    )
    assert update_response.status_code == 200
    update_body = update_response.json()
    assert update_body["data"]["capacidad"] == 750

    delete_response = await client.delete(
        f"/api/galpones/{galpon_id}", headers=auth_headers
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True


@pytest.mark.asyncio
async def test_list_lotes_by_galpon_endpoint(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]

    response = await client.get(
        f"/api/galpones/{galpon.id}/lotes",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1


@pytest.mark.asyncio
async def test_delete_galpon_con_lotes_activos_retorna_409(
    client, seeded_galpon_lote, auth_headers
):
    galpon = seeded_galpon_lote["galpon"]

    response = await client.delete(
        f"/api/galpones/{galpon.id}",
        headers=auth_headers,
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
