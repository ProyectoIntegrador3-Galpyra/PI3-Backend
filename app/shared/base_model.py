import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, TypeDecorator, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_ZERO_DATE_FALLBACK = datetime(2000, 1, 1, tzinfo=timezone.utc)


class SafeDateTime(TypeDecorator):
    """DateTime that tolerates MySQL/SQLite zero dates (0000-00-00 00:00:00)."""

    impl = DateTime
    cache_ok = True

    def result_processor(self, dialect, coltype):
        parent = super().result_processor(dialect, coltype)

        def process(value):
            if value is None:
                return None
            if isinstance(value, (bytes, bytearray)):
                value = value.decode("utf-8", errors="ignore")
            if isinstance(value, str) and (value.startswith("0000") or value == ""):
                return _ZERO_DATE_FALLBACK
            if parent is not None:
                try:
                    return parent(value)
                except (ValueError, TypeError):
                    return _ZERO_DATE_FALLBACK
            return value

        return process


class Base(DeclarativeBase):
    pass


class BaseModel(Base):
    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        SafeDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        SafeDateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        SafeDateTime(timezone=True),
        nullable=True,
    )

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)
