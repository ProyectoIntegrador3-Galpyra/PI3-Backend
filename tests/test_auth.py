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


@pytest.mark.asyncio
async def test_forgot_password_email_existente(client, seeded_admin):
    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": seeded_admin.email},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Si el correo está registrado" in body["message"]


@pytest.mark.asyncio
async def test_forgot_password_email_inexistente(client):
    response = await client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Si el correo está registrado" in body["message"]


@pytest.mark.asyncio
async def test_reset_password_token_valido(client, seeded_admin):
    from app.modules.auth.models import PasswordResetToken
    from sqlalchemy import select
    from datetime import timedelta

    # Generar token de reset
    import secrets
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    async with TestSessionLocal() as session:
        db_token = PasswordResetToken(
            usuario_id=seeded_admin.id,
            token=token,
            expires_at=expires_at,
        )
        session.add(db_token)
        await session.commit()

    # Reset password
    new_password = "NewSecure123!"
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "nueva_password": new_password},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "Contraseña actualizada" in body["message"]

    # Verificar que el token fue marcado como usado
    async with TestSessionLocal() as session:
        result = await session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        token_row = result.scalar_one_or_none()
        assert token_row.usado is True


@pytest.mark.asyncio
async def test_reset_password_token_expirado(client, seeded_admin):
    from app.modules.auth.models import PasswordResetToken
    from sqlalchemy import select
    from datetime import timedelta

    # Generar token expirado
    import secrets
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)

    async with TestSessionLocal() as session:
        db_token = PasswordResetToken(
            usuario_id=seeded_admin.id,
            token=token,
            expires_at=expires_at,
        )
        session.add(db_token)
        await session.commit()

    # Intentar reset
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "nueva_password": "NewSecure123!"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "Token inválido o expirado" in body["message"]


@pytest.mark.asyncio
async def test_reset_password_token_ya_usado(client, seeded_admin):
    from app.modules.auth.models import PasswordResetToken
    from sqlalchemy import select
    from datetime import timedelta

    # Generar token ya usado
    import secrets
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    async with TestSessionLocal() as session:
        db_token = PasswordResetToken(
            usuario_id=seeded_admin.id,
            token=token,
            expires_at=expires_at,
            usado=True,
        )
        session.add(db_token)
        await session.commit()

    # Intentar reset
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "nueva_password": "NewSecure123!"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert "Token inválido o expirado" in body["message"]


@pytest.mark.asyncio
async def test_reset_password_password_corta(client, seeded_admin):
    from app.modules.auth.models import PasswordResetToken
    from datetime import timedelta

    # Generar token válido
    import secrets
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    async with TestSessionLocal() as session:
        db_token = PasswordResetToken(
            usuario_id=seeded_admin.id,
            token=token,
            expires_at=expires_at,
        )
        session.add(db_token)
        await session.commit()

    # Intentar reset con password corta (< 8 caracteres)
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": token, "nueva_password": "Short1!"},
    )
    assert response.status_code == 422
