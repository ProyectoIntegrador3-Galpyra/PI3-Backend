"""add tokens_trazabilidad table

Revision ID: 20260324_000003
Revises: 20260324_000002
Create Date: 2026-03-24 00:00:03
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260324_000003"
down_revision: Union[str, None] = "20260324_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tokens_trazabilidad",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("lote_id", sa.String(36), sa.ForeignKey("lotes_aves.id"), nullable=False),
        sa.Column("token", sa.String(36), nullable=False),
        sa.Column("expira_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generado_por", sa.String(36), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tokens_trazabilidad_lote_id", "tokens_trazabilidad", ["lote_id"])
    op.create_index("ix_tokens_trazabilidad_token", "tokens_trazabilidad", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tokens_trazabilidad_token", table_name="tokens_trazabilidad")
    op.drop_index("ix_tokens_trazabilidad_lote_id", table_name="tokens_trazabilidad")
    op.drop_table("tokens_trazabilidad")
