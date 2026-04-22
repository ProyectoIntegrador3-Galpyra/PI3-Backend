from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.modules.auth.models import RefreshToken
from tests.conftest import PASSWORD_KEY, TEST_ADMIN_SECRET, TestSessionLocal


@pytest.mark.asyncio
async def test_login_refresh_logout(client, seeded_admin):
    login_response = await client.post(
        "/api/auth/login",
        json={"email": seeded_admin.email, PASSWORD_KEY: TEST_ADMIN_SECRET},
    )

    assert login_response.status_code == 200
    login_body = login_response.json()
    assert login_body["success"] is True
    assert login_body["data"]["access_token"]
    assert login_body["data"]["refresh_token"]

    refresh_response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": login_body["data"]["refresh_token"]},
    )
    assert refresh_response.status_code == 200
    refresh_body = refresh_response.json()
    assert refresh_body["success"] is True

    logout_response = await client.post(
        "/api/auth/logout",
        json={"refresh_token": refresh_body["data"]["refresh_token"]},
    )
    assert logout_response.status_code == 200
    assert logout_response.json()["success"] is True


@pytest.mark.asyncio
async def test_refresh_token_expira_en_siete_dias(client, seeded_admin):
    login_response = await client.post(
        "/api/auth/login",
        json={"email": seeded_admin.email, PASSWORD_KEY: TEST_ADMIN_SECRET},
    )
    assert login_response.status_code == 200

    async with TestSessionLocal() as session:
        result = await session.execute(
            select(RefreshToken).where(RefreshToken.user_id == seeded_admin.id)
        )
        token_row = result.scalars().first()
        assert token_row is not None

        expires_at = token_row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        delta = expires_at - datetime.now(timezone.utc)
        assert 6 <= delta.days <= 7


@pytest.mark.asyncio
async def test_me_requiere_token(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_con_token_valido(client, seeded_admin):
    login_response = await client.post(
        "/api/auth/login",
        json={"email": seeded_admin.email, PASSWORD_KEY: TEST_ADMIN_SECRET},
    )
    access_token = login_response.json()["data"]["access_token"]

    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == seeded_admin.email
