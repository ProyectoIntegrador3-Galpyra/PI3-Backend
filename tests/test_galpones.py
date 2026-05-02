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


@pytest.mark.asyncio
async def test_turno_activo_sin_asignacion(client, seeded_galpon_lote, auth_headers):
    galpon = seeded_galpon_lote["galpon"]

    response = await client.get(
        f"/api/galpones/{galpon.id}/turno-activo",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["turno"] in ["mañana", "tarde", "noche"]
    assert data["operario_nombre"] is None
    assert "Sin operario asignado" in data["mensaje"]


@pytest.mark.asyncio
async def test_asignar_turno_requiere_admin(client, seeded_galpon_lote):
    from tests.conftest import PASSWORD_KEY, TEST_ADMIN_SECRET
    from app.modules.auth.models import Usuario
    from app.core.security import hash_password
    from app.shared.enums import RolUsuario
    from tests.conftest import TestSessionLocal
    from datetime import date

    # Crear usuario no admin
    async with TestSessionLocal() as session:
        productor = Usuario(
            nombre="Productor Test",
            email="productor@test.com",
            password_hash=hash_password(TEST_ADMIN_SECRET),
            rol=RolUsuario.PRODUCTOR,
            is_active=True,
        )
        session.add(productor)
        await session.commit()

    # Intentar asignar turno como no-admin
    login_response = await client.post(
        "/api/auth/login",
        json={"email": "productor@test.com", PASSWORD_KEY: TEST_ADMIN_SECRET},
    )
    non_admin_token = login_response.json()["data"]["access_token"]

    galpon = seeded_galpon_lote["galpon"]
    response = await client.post(
        f"/api/galpones/{galpon.id}/turno-activo",
        json={
            "usuario_id": seeded_galpon_lote["admin"].id,
            "turno": "tarde",
            "fecha": str(date.today()),
        },
        headers={"Authorization": f"Bearer {non_admin_token}"},
    )
    assert response.status_code == 403
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_asignar_turno_admin(client, seeded_galpon_lote, auth_headers):
    from datetime import date

    galpon = seeded_galpon_lote["galpon"]
    admin = seeded_galpon_lote["admin"]

    response = await client.post(
        f"/api/galpones/{galpon.id}/turno-activo",
        json={
            "usuario_id": admin.id,
            "turno": "tarde",
            "fecha": str(date.today()),
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_get_turnos_historial(client, seeded_galpon_lote, auth_headers):
    from datetime import date

    galpon = seeded_galpon_lote["galpon"]
    admin = seeded_galpon_lote["admin"]

    # Asignar un turno
    await client.post(
        f"/api/galpones/{galpon.id}/turno-activo",
        json={
            "usuario_id": admin.id,
            "turno": "mañana",
            "fecha": str(date.today()),
        },
        headers=auth_headers,
    )

    # Obtener historial
    response = await client.get(
        f"/api/galpones/{galpon.id}/turnos-historial",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["data"]) >= 1
    assert body["data"][0]["operario_nombre"] == admin.nombre
