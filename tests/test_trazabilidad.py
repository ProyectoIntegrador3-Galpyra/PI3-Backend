from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.modules.trazabilidad.models import TokenTrazabilidad
from tests.conftest import PASSWORD_KEY, TEST_ADMIN_SECRET, TestSessionLocal


@pytest.mark.asyncio
async def test_generar_token_requiere_auth(client, seeded_galpon_lote):
    lote = seeded_galpon_lote["lote"]
    response = await client.post(
        "/api/trazabilidad/token",
        json={"lote_id": lote.id, "dias_vigencia": 30},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_generar_token_exitoso(client, seeded_galpon_lote):
    admin = seeded_galpon_lote["admin"]
    lote = seeded_galpon_lote["lote"]

    login = await client.post(
        "/api/auth/login",
        json={"email": admin.email, PASSWORD_KEY: TEST_ADMIN_SECRET},
    )
    access_token = login.json()["data"]["access_token"]

    response = await client.post(
        "/api/trazabilidad/token",
        json={"lote_id": lote.id, "dias_vigencia": 30},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert "token" in data
    assert data["lote_id"] == lote.id
    assert "expira_en" in data


@pytest.mark.asyncio
async def test_consulta_publica(client, seeded_galpon_lote):
    admin = seeded_galpon_lote["admin"]
    lote = seeded_galpon_lote["lote"]

    login = await client.post(
        "/api/auth/login",
        json={"email": admin.email, PASSWORD_KEY: TEST_ADMIN_SECRET},
    )
    access_token = login.json()["data"]["access_token"]

    gen_response = await client.post(
        "/api/trazabilidad/token",
        json={"lote_id": lote.id, "dias_vigencia": 30},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    token = gen_response.json()["data"]["token"]

    # Consulta pública — sin JWT
    response = await client.get(f"/api/trazabilidad/{token}")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["lote"]["id"] == lote.id
    assert isinstance(data["eventos_sanitarios"], list)
    assert "expira_en" in data
    assert isinstance(data["expira_en"], str)


@pytest.mark.asyncio
async def test_token_expirado(client, seeded_galpon_lote):
    admin = seeded_galpon_lote["admin"]
    lote = seeded_galpon_lote["lote"]

    async with TestSessionLocal() as session:
        tk = TokenTrazabilidad(
            lote_id=lote.id,
            token=str(uuid4()),
            expira_en=datetime.now(timezone.utc) - timedelta(days=1),
            generado_por=admin.id,
        )
        session.add(tk)
        await session.commit()
        await session.refresh(tk)
        token_value = tk.token

    response = await client.get(f"/api/trazabilidad/{token_value}")
    assert response.status_code == 410
