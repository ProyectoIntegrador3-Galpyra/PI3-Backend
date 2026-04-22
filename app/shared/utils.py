from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | datetime | None) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def update_model_from_dict(model: Any, payload: dict[str, Any]) -> None:
    for field, value in payload.items():
        if hasattr(model, field):
            setattr(model, field, value)
