"""update tipo evento sanitario enum values

Revision ID: 20260324_000002
Revises: 20260313_000001
Create Date: 2026-03-24 00:00:02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260324_000002"
down_revision: Union[str, None] = "20260313_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


OLD_VALUES = ("VACUNACION", "ENFERMEDAD", "TRATAMIENTO", "REVISION")
NEW_VALUES = ("VACUNACION", "DIAGNOSTICO", "TRATAMIENTO", "INSPECCION")


def _enum_sql(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            "UPDATE eventos_sanitarios "
            "SET tipo_evento = 'DIAGNOSTICO' "
            "WHERE tipo_evento = 'ENFERMEDAD'"
        )
        op.execute(
            "UPDATE eventos_sanitarios "
            "SET tipo_evento = 'INSPECCION' "
            "WHERE tipo_evento = 'REVISION'"
        )
        op.execute(
            "ALTER TABLE eventos_sanitarios "
            f"MODIFY tipo_evento ENUM({_enum_sql(NEW_VALUES)}) NOT NULL"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute(
            "UPDATE eventos_sanitarios "
            "SET tipo_evento = 'ENFERMEDAD' "
            "WHERE tipo_evento = 'DIAGNOSTICO'"
        )
        op.execute(
            "UPDATE eventos_sanitarios "
            "SET tipo_evento = 'REVISION' "
            "WHERE tipo_evento = 'INSPECCION'"
        )
        op.execute(
            "ALTER TABLE eventos_sanitarios "
            f"MODIFY tipo_evento ENUM({_enum_sql(OLD_VALUES)}) NOT NULL"
        )
