import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(
    subject: str,
    rol: str | None = None,
    expires_minutes: int | None = None,
) -> str:
    expire_delta = timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes,
    )
    expire_at = _utc_now() + expire_delta

    payload: dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "exp": expire_at,
        "iat": _utc_now(),
    }
    if rol is not None:
        payload["rol"] = rol

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def verify_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:
        raise ValueError("Token invalido o expirado") from exc

    return payload


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(
    expires_days: int | None = None,
) -> tuple[str, str, datetime]:
    raw_token = secrets.token_urlsafe(48)
    expires_at = _utc_now() + timedelta(
        days=expires_days or settings.refresh_token_expire_days,
    )

    return raw_token, hash_refresh_token(raw_token), expires_at


def verify_refresh_token(raw_token: str, stored_hash: str) -> bool:
    calculated_hash = hash_refresh_token(raw_token)
    return hmac.compare_digest(calculated_hash, stored_hash)
