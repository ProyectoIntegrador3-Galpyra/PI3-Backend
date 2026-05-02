"""add galpon_turnos table for shift assignments

Revision ID: 20260501_000006
Revises: 20260501_000005
Create Date: 2026-05-01 00:00:06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260501_000006"
down_revision: Union[str, None] = "20260501_000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


turno_enum = sa.Enum("mañana", "tarde", "noche", name="turno")


def upgrade() -> None:
    op.create_table(
        "galpon_turnos",
        sa.Column("galpon_id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.String(length=36), nullable=False),
        sa.Column("turno", turno_enum, nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["galpon_id"], ["galpones.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_galpon_turnos_galpon_id", "galpon_turnos", ["galpon_id"], unique=False)
    op.create_index("ix_galpon_turnos_usuario_id", "galpon_turnos", ["usuario_id"], unique=False)
    op.create_index("ix_galpon_turnos_fecha", "galpon_turnos", ["fecha"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_galpon_turnos_fecha", table_name="galpon_turnos")
    op.drop_index("ix_galpon_turnos_usuario_id", table_name="galpon_turnos")
    op.drop_index("ix_galpon_turnos_galpon_id", table_name="galpon_turnos")
    op.drop_table("galpon_turnos")
