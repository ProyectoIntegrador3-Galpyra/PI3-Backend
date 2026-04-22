from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.modules.alimentacion.models import AlimentacionRegistro
from app.modules.auth.models import Usuario
from app.modules.aves.models import LoteAve, MovimientoAve
from app.modules.galpones.models import Galpon
from app.modules.inventario_foto.models import InventarioFotoJob
from app.modules.produccion.models import ProduccionHuevo
from app.modules.sanidad.models import EventoSanitario
from app.shared.enums import (
    EstadoGalpon,
    EstadoInventarioFoto,
    EstadoLote,
    RolUsuario,
    TipoEventoSanitario,
    TipoMovimientoAve,
)


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        existing_admin = await session.scalar(
            select(Usuario).where(Usuario.email == "admin@galpyra.com")
        )
        if existing_admin is None:
            admin = Usuario(
                nombre="Administrador GALPyra",
                email="admin@galpyra.com",
                password_hash=hash_password("Admin123*"),
                rol=RolUsuario.ADMIN,
                is_active=True,
            )
            session.add(admin)
            await session.flush()
        else:
            admin = existing_admin

        seed_suffix = uuid4().hex[:8]

        galpon_1 = Galpon(
            nombre=f"Galpon Norte {seed_suffix}",
            ubicacion="Vereda La Cuchilla, Santander",
            capacidad=1200,
            estado=EstadoGalpon.ACTIVO,
            descripcion="Galpon principal para lote de postura",
            propietario_id=admin.id,
        )
        galpon_2 = Galpon(
            nombre=f"Galpon Sur {seed_suffix}",
            ubicacion="Vereda El Cedro, Santander",
            capacidad=1000,
            estado=EstadoGalpon.ACTIVO,
            descripcion="Galpon de respaldo",
            propietario_id=admin.id,
        )
        session.add_all([galpon_1, galpon_2])
        await session.flush()

        lote_1 = LoteAve(
            codigo_lote=f"L-2026-{seed_suffix}-001",
            tipo_ave="PONEDORA",
            raza="Hy-Line Brown",
            cantidad_inicial=900,
            cantidad_actual=900,
            fecha_ingreso=datetime.now(timezone.utc) - timedelta(days=60),
            galpon_id=galpon_1.id,
            estado=EstadoLote.ACTIVO,
        )
        lote_2 = LoteAve(
            codigo_lote=f"L-2026-{seed_suffix}-002",
            tipo_ave="PONEDORA",
            raza="Lohmann Brown",
            cantidad_inicial=800,
            cantidad_actual=800,
            fecha_ingreso=datetime.now(timezone.utc) - timedelta(days=45),
            galpon_id=galpon_2.id,
            estado=EstadoLote.ACTIVO,
        )
        session.add_all([lote_1, lote_2])
        await session.flush()

        mov_1 = MovimientoAve(
            lote_id=lote_1.id,
            tipo_movimiento=TipoMovimientoAve.INGRESO,
            cantidad=50,
            causa="Ingreso de reposicion",
            fecha=datetime.now(timezone.utc) - timedelta(days=20),
            observaciones="Ingreso por ampliacion de lote",
        )
        lote_1.cantidad_actual += 50

        mov_2 = MovimientoAve(
            lote_id=lote_2.id,
            tipo_movimiento=TipoMovimientoAve.MORTALIDAD,
            cantidad=15,
            causa="Mortalidad natural",
            fecha=datetime.now(timezone.utc) - timedelta(days=10),
            observaciones="Sin signos de brote",
        )
        lote_2.cantidad_actual -= 15
        session.add_all([mov_1, mov_2])

        prod_1 = ProduccionHuevo(
            galpon_id=galpon_1.id,
            lote_id=lote_1.id,
            fecha=datetime.now(timezone.utc) - timedelta(days=1),
            cantidad=620,
            huevos_rotos=8,
            observaciones="Produccion estable",
        )
        prod_2 = ProduccionHuevo(
            galpon_id=galpon_2.id,
            lote_id=lote_2.id,
            fecha=datetime.now(timezone.utc) - timedelta(days=1),
            cantidad=540,
            huevos_rotos=12,
            observaciones="Leve baja por clima",
        )
        session.add_all([prod_1, prod_2])

        san_1 = EventoSanitario(
            lote_id=lote_1.id,
            galpon_id=galpon_1.id,
            tipo_evento=TipoEventoSanitario.VACUNACION,
            descripcion="Vacunacion de refuerzo",
            producto="Vacuna Newcastle",
            dosis="0.5 ml por ave",
            responsable="Tec. Javier Perez",
            fecha=datetime.now(timezone.utc) - timedelta(days=7),
            observaciones="Sin reacciones adversas",
        )
        san_2 = EventoSanitario(
            lote_id=lote_2.id,
            galpon_id=galpon_2.id,
            tipo_evento=TipoEventoSanitario.INSPECCION,
            descripcion="Revision rutinaria",
            producto="N/A",
            dosis="N/A",
            responsable="Tec. Luisa Rueda",
            fecha=datetime.now(timezone.utc) - timedelta(days=3),
            observaciones="Estado general favorable",
        )
        session.add_all([san_1, san_2])

        ali_1 = AlimentacionRegistro(
            galpon_id=galpon_1.id,
            lote_id=lote_1.id,
            fecha=datetime.now(timezone.utc) - timedelta(days=1),
            tipo_alimento="Balanceado postura A",
            cantidad_kg=38.5,
            costo=210000,
            observaciones="Racion completa manana",
        )
        ali_2 = AlimentacionRegistro(
            galpon_id=galpon_2.id,
            lote_id=lote_2.id,
            fecha=datetime.now(timezone.utc) - timedelta(days=1),
            tipo_alimento="Balanceado postura B",
            cantidad_kg=34.0,
            costo=186000,
            observaciones="Sin novedades",
        )
        session.add_all([ali_1, ali_2])

        inventario_job = InventarioFotoJob(
            lote_id=lote_1.id,
            galpon_id=galpon_1.id,
            image_url="tmp_uploads/seed_lote1.jpg",
            filename="seed_lote1.jpg",
            conteo_estimado=935,
            conteo_confirmado=930,
            origen="cloud",
            estado=EstadoInventarioFoto.CONFIRMADO,
            bounding_boxes_json=[],
            procesado_en=datetime.now(timezone.utc) - timedelta(hours=2),
            confirmado_en=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        session.add(inventario_job)

        await session.commit()


if __name__ == "__main__":
    asyncio.run(seed())
