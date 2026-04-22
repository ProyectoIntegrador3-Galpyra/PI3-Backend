import pytest
import pytest_asyncio
from tests.conftest import PASSWORD_KEY, TEST_ADMIN_SECRET, TestSessionLocal

from app.core.security import hash_password
from app.modules.auth.models import Usuario
from app.shared.enums import RolUsuario


@pytest_asyncio.fixture
async def productor_headers(client, seeded_admin):
    """Token de un usuario con rol PRODUCTOR para verificar que se rechaza."""
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

    response = await client.post(
        "/api/auth/login",
        json={"email": "productor@test.com", PASSWORD_KEY: TEST_ADMIN_SECRET},
    )
    token = response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ─── GET /api/admin/users ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_users_ok(client, auth_headers, seeded_admin):
    response = await client.get("/api/admin/users", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    emails = [u["email"] for u in body["data"]]
    assert seeded_admin.email in emails


@pytest.mark.asyncio
async def test_admin_list_users_requiere_admin(client, productor_headers):
    response = await client.get("/api/admin/users", headers=productor_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users_sin_token(client, seeded_admin):
    response = await client.get("/api/admin/users")
    assert response.status_code == 401


# ─── POST /api/admin/users ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_create_user_ok(client, auth_headers):
    payload = {
        "nombre": "Nuevo Operador",
        "email": "operador@galpyra.com",
        "password": "Segura123*",
        "rol": "PRODUCTOR",
    }
    response = await client.post("/api/admin/users", json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "operador@galpyra.com"
    assert body["data"]["rol"] == "PRODUCTOR"


@pytest.mark.asyncio
async def test_admin_create_user_email_duplicado(client, auth_headers, seeded_admin):
    payload = {
        "nombre": "Duplicado",
        "email": seeded_admin.email,
        "password": "Segura123*",
        "rol": "PRODUCTOR",
    }
    response = await client.post("/api/admin/users", json=payload, headers=auth_headers)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_admin_create_user_requiere_admin(client, productor_headers):
    payload = {
        "nombre": "X",
        "email": "x@x.com",
        "password": "password123",
        "rol": "PRODUCTOR",
    }
    response = await client.post("/api/admin/users", json=payload, headers=productor_headers)
    assert response.status_code == 403


# ─── PATCH /api/admin/users/{id} ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_update_user_nombre(client, auth_headers, seeded_admin):
    response = await client.patch(
        f"/api/admin/users/{seeded_admin.id}",
        json={"nombre": "Nuevo Nombre Admin"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["data"]["nombre"] == "Nuevo Nombre Admin"


@pytest.mark.asyncio
async def test_admin_update_user_no_encontrado(client, auth_headers):
    response = await client.patch(
        "/api/admin/users/uuid-inexistente",
        json={"nombre": "X"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ─── DELETE /api/admin/users/{id} ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_delete_user_ok(client, auth_headers):
    # Crear usuario a eliminar
    create_resp = await client.post(
        "/api/admin/users",
        json={
            "nombre": "Temporal",
            "email": "temporal@galpyra.com",
            "password": "Segura123*",
            "rol": "PRODUCTOR",
        },
        headers=auth_headers,
    )
    user_id = create_resp.json()["data"]["id"]

    delete_resp = await client.delete(
        f"/api/admin/users/{user_id}", headers=auth_headers
    )
    assert delete_resp.status_code == 200
    assert delete_resp.json()["success"] is True


@pytest.mark.asyncio
async def test_admin_delete_propio_usuario_rechazado(client, auth_headers, seeded_admin):
    response = await client.delete(
        f"/api/admin/users/{seeded_admin.id}", headers=auth_headers
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_delete_no_encontrado(client, auth_headers):
    response = await client.delete(
        "/api/admin/users/uuid-inexistente", headers=auth_headers
    )
    assert response.status_code == 404


# ─── JWT contiene rol ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_jwt_contiene_rol(client, seeded_admin):
    import base64
    import json

    response = await client.post(
        "/api/auth/login",
        json={"email": seeded_admin.email, PASSWORD_KEY: TEST_ADMIN_SECRET},
    )
    assert response.status_code == 200
    token = response.json()["data"]["access_token"]

    # Decodificar payload del JWT (sin verificar firma)
    parts = token.split(".")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded))

    assert "rol" in payload
    assert payload["rol"] == RolUsuario.ADMIN.value
