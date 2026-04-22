"""initial schema

Revision ID: 20260313_000001
Revises:
Create Date: 2026-03-13 00:00:01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260313_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


rol_usuario_enum = sa.Enum("ADMIN", "PRODUCTOR", "TECNICO", name="rolusuario")
estado_galpon_enum = sa.Enum(
    "ACTIVO",
    "INACTIVO",
    "MANTENIMIENTO",
    name="estadogalpon",
)
tipo_movimiento_enum = sa.Enum(
    "INGRESO",
    "MORTALIDAD",
    "AJUSTE",
    name="tipomovimientoave",
)
estado_lote_enum = sa.Enum("ACTIVO", "CERRADO", name="estadolote")
tipo_evento_sanitario_enum = sa.Enum(
    "VACUNACION",
    "ENFERMEDAD",
    "TRATAMIENTO",
    "REVISION",
    name="tipoeventosanitario",
)
estado_sync_enum = sa.Enum("PENDIENTE", "PROCESADO", "ERROR", name="estadosync")
estado_inventario_enum = sa.Enum(
    "PENDIENTE",
    "PROCESANDO",
    "PROCESADO",
    "CONFIRMADO",
    "ERROR",
    name="estadoinventariofoto",
)


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("nombre", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol", rol_usuario_enum, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False)

    op.create_table(
        "galpones",
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("ubicacion", sa.String(length=200), nullable=False),
        sa.Column("capacidad", sa.Integer(), nullable=False),
        sa.Column("estado", estado_galpon_enum, nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("propietario_id", sa.String(length=36), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["propietario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_galpones_propietario_id", "galpones", ["propietario_id"], unique=False)

    op.create_table(
        "lotes_aves",
        sa.Column("codigo_lote", sa.String(length=80), nullable=False),
        sa.Column("tipo_ave", sa.String(length=80), nullable=False),
        sa.Column("raza", sa.String(length=120), nullable=False),
        sa.Column("cantidad_inicial", sa.Integer(), nullable=False),
        sa.Column("cantidad_actual", sa.Integer(), nullable=False),
        sa.Column("fecha_ingreso", sa.DateTime(timezone=True), nullable=False),
        sa.Column("galpon_id", sa.String(length=36), nullable=False),
        sa.Column("estado", estado_lote_enum, nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["galpon_id"], ["galpones.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codigo_lote"),
    )
    op.create_index("ix_lotes_aves_codigo_lote", "lotes_aves", ["codigo_lote"], unique=True)
    op.create_index("ix_lotes_aves_galpon_id", "lotes_aves", ["galpon_id"], unique=False)

    op.create_table(
        "movimientos_aves",
        sa.Column("lote_id", sa.String(length=36), nullable=False),
        sa.Column("tipo_movimiento", tipo_movimiento_enum, nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("causa", sa.String(length=120), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes_aves.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_movimientos_aves_lote_id", "movimientos_aves", ["lote_id"], unique=False)

    op.create_table(
        "produccion_huevos",
        sa.Column("galpon_id", sa.String(length=36), nullable=False),
        sa.Column("lote_id", sa.String(length=36), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cantidad", sa.Integer(), nullable=False),
        sa.Column("huevos_rotos", sa.Integer(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["galpon_id"], ["galpones.id"]),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes_aves.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_produccion_huevos_fecha", "produccion_huevos", ["fecha"], unique=False)
    op.create_index("ix_produccion_huevos_galpon_id", "produccion_huevos", ["galpon_id"], unique=False)
    op.create_index("ix_produccion_huevos_lote_id", "produccion_huevos", ["lote_id"], unique=False)

    op.create_table(
        "eventos_sanitarios",
        sa.Column("lote_id", sa.String(length=36), nullable=False),
        sa.Column("galpon_id", sa.String(length=36), nullable=False),
        sa.Column("tipo_evento", tipo_evento_sanitario_enum, nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("producto", sa.String(length=180), nullable=False),
        sa.Column("dosis", sa.String(length=120), nullable=False),
        sa.Column("responsable", sa.String(length=120), nullable=False),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["galpon_id"], ["galpones.id"]),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes_aves.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eventos_sanitarios_fecha", "eventos_sanitarios", ["fecha"], unique=False)
    op.create_index("ix_eventos_sanitarios_galpon_id", "eventos_sanitarios", ["galpon_id"], unique=False)
    op.create_index("ix_eventos_sanitarios_lote_id", "eventos_sanitarios", ["lote_id"], unique=False)

    op.create_table(
        "alimentacion_registros",
        sa.Column("galpon_id", sa.String(length=36), nullable=False),
        sa.Column("lote_id", sa.String(length=36), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tipo_alimento", sa.String(length=120), nullable=False),
        sa.Column("cantidad_kg", sa.Float(), nullable=False),
        sa.Column("costo", sa.Float(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["galpon_id"], ["galpones.id"]),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes_aves.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alimentacion_registros_fecha", "alimentacion_registros", ["fecha"], unique=False)
    op.create_index("ix_alimentacion_registros_galpon_id", "alimentacion_registros", ["galpon_id"], unique=False)
    op.create_index("ix_alimentacion_registros_lote_id", "alimentacion_registros", ["lote_id"], unique=False)

    op.create_table(
        "reportes_generados",
        sa.Column("tipo", sa.String(length=80), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("formato", sa.String(length=20), nullable=False),
        sa.Column("url_archivo", sa.String(length=300), nullable=True),
        sa.Column("generado_por", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["generado_por"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reportes_generados_generado_por", "reportes_generados", ["generado_por"], unique=False)

    op.create_table(
        "sync_logs",
        sa.Column("operacion", sa.String(length=40), nullable=False),
        sa.Column("entidad", sa.String(length=80), nullable=False),
        sa.Column("entidad_id", sa.String(length=36), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("cliente_created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("procesado_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", estado_sync_enum, nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sync_logs_entidad_id", "sync_logs", ["entidad_id"], unique=False)
    op.create_index("ix_sync_logs_estado", "sync_logs", ["estado"], unique=False)

    op.create_table(
        "inventario_foto_jobs",
        sa.Column("lote_id", sa.String(length=36), nullable=True),
        sa.Column("galpon_id", sa.String(length=36), nullable=True),
        sa.Column("image_url", sa.String(length=300), nullable=True),
        sa.Column("filename", sa.String(length=255), nullable=True),
        sa.Column("conteo_estimado", sa.Integer(), nullable=True),
        sa.Column("conteo_confirmado", sa.Integer(), nullable=True),
        sa.Column("origen", sa.String(length=30), nullable=False),
        sa.Column("estado", estado_inventario_enum, nullable=False),
        sa.Column("bounding_boxes_json", sa.JSON(), nullable=True),
        sa.Column("procesado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["galpon_id"], ["galpones.id"]),
        sa.ForeignKeyConstraint(["lote_id"], ["lotes_aves.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_inventario_foto_jobs_galpon_id", "inventario_foto_jobs", ["galpon_id"], unique=False)
    op.create_index("ix_inventario_foto_jobs_lote_id", "inventario_foto_jobs", ["lote_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_inventario_foto_jobs_lote_id", table_name="inventario_foto_jobs")
    op.drop_index("ix_inventario_foto_jobs_galpon_id", table_name="inventario_foto_jobs")
    op.drop_table("inventario_foto_jobs")

    op.drop_index("ix_sync_logs_estado", table_name="sync_logs")
    op.drop_index("ix_sync_logs_entidad_id", table_name="sync_logs")
    op.drop_table("sync_logs")

    op.drop_index("ix_reportes_generados_generado_por", table_name="reportes_generados")
    op.drop_table("reportes_generados")

    op.drop_index("ix_alimentacion_registros_lote_id", table_name="alimentacion_registros")
    op.drop_index("ix_alimentacion_registros_galpon_id", table_name="alimentacion_registros")
    op.drop_index("ix_alimentacion_registros_fecha", table_name="alimentacion_registros")
    op.drop_table("alimentacion_registros")

    op.drop_index("ix_eventos_sanitarios_lote_id", table_name="eventos_sanitarios")
    op.drop_index("ix_eventos_sanitarios_galpon_id", table_name="eventos_sanitarios")
    op.drop_index("ix_eventos_sanitarios_fecha", table_name="eventos_sanitarios")
    op.drop_table("eventos_sanitarios")

    op.drop_index("ix_produccion_huevos_lote_id", table_name="produccion_huevos")
    op.drop_index("ix_produccion_huevos_galpon_id", table_name="produccion_huevos")
    op.drop_index("ix_produccion_huevos_fecha", table_name="produccion_huevos")
    op.drop_table("produccion_huevos")

    op.drop_index("ix_movimientos_aves_lote_id", table_name="movimientos_aves")
    op.drop_table("movimientos_aves")

    op.drop_index("ix_lotes_aves_galpon_id", table_name="lotes_aves")
    op.drop_index("ix_lotes_aves_codigo_lote", table_name="lotes_aves")
    op.drop_table("lotes_aves")

    op.drop_index("ix_galpones_propietario_id", table_name="galpones")
    op.drop_table("galpones")

    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")

    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
