"""Importa modelos para que Alembic detecte metadata completa."""

from app.modules.alimentacion import models as alimentacion_models
from app.modules.auth import models as auth_models
from app.modules.aves import models as aves_models
from app.modules.galpones import models as galpones_models
from app.modules.inventario_foto import models as inventario_models
from app.modules.produccion import models as produccion_models
from app.modules.reportes import models as reportes_models
from app.modules.sanidad import models as sanidad_models
from app.modules.sync import models as sync_models

__all__ = [
    "alimentacion_models",
    "auth_models",
    "aves_models",
    "galpones_models",
    "inventario_models",
    "produccion_models",
    "reportes_models",
    "sanidad_models",
    "sync_models",
]
