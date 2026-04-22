from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.shared.base_model import Base

# Columnas añadidas después de la creación inicial de la DB.
# Cada entrada: (tabla, columna, definición SQL).
_PENDING_COLUMNS: list[tuple[str, str, str]] = [
    ("lotes_aves", "peso_promedio_ingreso_kg", "REAL"),
]

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600,
    future=True,
    echo=settings.environment == "development",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
    autocommit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session


async def _apply_pending_columns(connection) -> None:
    """Añade columnas nuevas a tablas existentes sin romper DBs ya creadas."""
    for table, column, definition in _PENDING_COLUMNS:
        try:
            await connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            )
        except Exception:
            pass  # La columna ya existe


async def init_db() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await _apply_pending_columns(connection)
