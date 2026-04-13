"""add lote peso ingreso and produccion icontec fields

Revision ID: 20260412_000004
Revises: 20260324_000003
Create Date: 2026-04-12 00:00:04
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "20260412_000004"
down_revision: Union[str, None] = "20260324_000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lotes_aves",
        sa.Column("peso_promedio_ingreso_kg", sa.Numeric(5, 2), nullable=True),
    )

    op.add_column(
        "produccion_huevos",
        sa.Column(
            "huevos_yumbo",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "produccion_huevos",
        sa.Column(
            "huevos_aaa",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "produccion_huevos",
        sa.Column(
            "huevos_aa",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "produccion_huevos",
        sa.Column(
            "huevos_a",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "produccion_huevos",
        sa.Column(
            "huevos_b",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "produccion_huevos",
        sa.Column(
            "huevos_c",
            mysql.INTEGER(unsigned=True),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("produccion_huevos", "huevos_c")
    op.drop_column("produccion_huevos", "huevos_b")
    op.drop_column("produccion_huevos", "huevos_a")
    op.drop_column("produccion_huevos", "huevos_aa")
    op.drop_column("produccion_huevos", "huevos_aaa")
    op.drop_column("produccion_huevos", "huevos_yumbo")
    op.drop_column("lotes_aves", "peso_promedio_ingreso_kg")
