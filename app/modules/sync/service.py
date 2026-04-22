from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.alimentacion.models import AlimentacionRegistro
from app.modules.aves.models import LoteAve, MovimientoAve
from app.modules.galpones.models import Galpon
from app.modules.produccion.models import ProduccionHuevo
from app.modules.sanidad.models import EventoSanitario
from app.modules.sync.models import SyncLog
from app.modules.sync.schemas import (
    SyncLogOut,
    SyncOperation,
    SyncOperationResult,
    SyncRequest,
    SyncResponse,
)
from app.shared.enums import (
    EstadoGalpon,
    EstadoLote,
    EstadoSync,
    TipoEventoSanitario,
    TipoMovimientoAve,
)
from app.shared.utils import parse_datetime, update_model_from_dict


LWW_DESCARTADO = "Descartado por Last Write Wins"


class SyncService:
    @staticmethod
    def _is_stale_update(
        current_updated_at: datetime,
        payload_updated_at: datetime,
    ) -> bool:
        current = current_updated_at
        if current.tzinfo is None:
            current = current.replace(tzinfo=timezone.utc)
        return payload_updated_at <= current

    @staticmethod
    async def _crear_movimiento(
        db: AsyncSession,
        entity_id: str,
        data: dict,
    ) -> str:
        required_fields = [
            "lote_id",
            "tipo_movimiento",
            "cantidad",
            "causa",
            "fecha",
        ]
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise AppException(message=f"Faltan campos requeridos: {', '.join(missing)}")

        lote_result = await db.execute(select(LoteAve).where(LoteAve.id == data["lote_id"]))
        lote = lote_result.scalar_one_or_none()
        if lote is None:
            raise AppException(message="Lote no encontrado para sync de movimiento")

        tipo = TipoMovimientoAve(data["tipo_movimiento"])
        cantidad = int(data["cantidad"])

        if tipo == TipoMovimientoAve.MORTALIDAD:
            if lote.cantidad_actual < cantidad:
                raise AppException(message="Mortalidad sync supera cantidad actual")
            lote.cantidad_actual -= cantidad
        else:
            lote.cantidad_actual += cantidad

        row = MovimientoAve(
            id=entity_id,
            lote_id=data["lote_id"],
            tipo_movimiento=tipo,
            cantidad=cantidad,
            causa=data["causa"],
            fecha=parse_datetime(data["fecha"]),
            observaciones=data.get("observaciones"),
        )
        db.add(row)
        return "Movimiento creado por sync"

    @staticmethod
    async def procesar_batch(db: AsyncSession, payload: SyncRequest) -> SyncResponse:
        procesadas = 0
        fallidas = 0
        detalles: list[SyncOperationResult] = []

        for operation in payload.operaciones:
            log = SyncLog(
                operacion=operation.operacion,
                entidad=operation.entidad,
                entidad_id=operation.payload.get("id", operation.id),
                payload_json=operation.payload,
                cliente_created_at=operation.created_at,
                estado=EstadoSync.PENDIENTE,
            )
            db.add(log)
            await db.flush()

            try:
                message = await SyncService._procesar_operacion(db, operation)

                log.estado = EstadoSync.PROCESADO
                log.mensaje = message
                log.procesado_at = datetime.now(timezone.utc)
                procesadas += 1
                detalles.append(
                    SyncOperationResult(
                        id=operation.id,
                        entidad=operation.entidad,
                        estado=EstadoSync.PROCESADO,
                        mensaje=message,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                log.estado = EstadoSync.ERROR
                log.mensaje = str(exc)
                log.procesado_at = datetime.now(timezone.utc)
                fallidas += 1
                detalles.append(
                    SyncOperationResult(
                        id=operation.id,
                        entidad=operation.entidad,
                        estado=EstadoSync.ERROR,
                        mensaje=str(exc),
                    )
                )

        await db.commit()

        return SyncResponse(procesadas=procesadas, fallidas=fallidas, detalles=detalles)

    @staticmethod
    async def _procesar_operacion(db: AsyncSession, operation: SyncOperation) -> str:
        operacion = operation.operacion.upper()

        if operacion == "DELETE":
            return await SyncService._soft_delete_entidad(db, operation)

        if operation.entidad in {"produccion_huevos", "produccion"}:
            return await SyncService._upsert_produccion(db, operation)
        if operation.entidad in {"movimiento_aves", "movimientos_aves"}:
            return await SyncService._upsert_movimiento(db, operation)
        if operation.entidad in {"galpones", "galpon"}:
            return await SyncService._upsert_galpon(db, operation)
        if operation.entidad in {"lotes_aves", "lote_aves", "lotes"}:
            return await SyncService._upsert_lote(db, operation)
        if operation.entidad in {"eventos_sanitarios", "evento_sanitario"}:
            return await SyncService._upsert_evento_sanitario(db, operation)
        if operation.entidad in {"alimentacion_registros", "alimentacion"}:
            return await SyncService._upsert_alimentacion(db, operation)

        raise AppException(
            message=f"Entidad {operation.entidad} no soportada para sync"
        )

    @staticmethod
    async def _soft_delete_entidad(db: AsyncSession, operation: SyncOperation) -> str:
        model_by_entidad = {
            "produccion_huevos": ProduccionHuevo,
            "produccion": ProduccionHuevo,
            "movimiento_aves": MovimientoAve,
            "movimientos_aves": MovimientoAve,
            "galpones": Galpon,
            "galpon": Galpon,
            "lotes_aves": LoteAve,
            "lote_aves": LoteAve,
            "lotes": LoteAve,
            "eventos_sanitarios": EventoSanitario,
            "evento_sanitario": EventoSanitario,
            "alimentacion_registros": AlimentacionRegistro,
            "alimentacion": AlimentacionRegistro,
        }
        model = model_by_entidad.get(operation.entidad)
        if model is None:
            raise AppException(
                message=f"Entidad {operation.entidad} no soportada para DELETE"
            )

        data = dict(operation.payload)
        entity_id = data.get("id")
        if not entity_id:
            raise AppException(message="DELETE sync requiere payload.id")

        payload_updated_at = (
            parse_datetime(data.get("updated_at")) or operation.created_at
        )
        result = await db.execute(select(model).where(model.id == entity_id))
        row = result.scalar_one_or_none()
        if row is None:
            return "No existe para eliminar"

        if SyncService._is_stale_update(row.updated_at, payload_updated_at):
            return LWW_DESCARTADO

        row.deleted_at = datetime.now(timezone.utc)
        return "Eliminado por sync"

    @staticmethod
    async def list_logs(db: AsyncSession) -> list[SyncLogOut]:
        result = await db.execute(
            select(SyncLog)
            .where(SyncLog.deleted_at.is_(None))
            .order_by(SyncLog.created_at.desc())
        )
        return [SyncLogOut.model_validate(item) for item in result.scalars().all()]

    @staticmethod
    async def _upsert_produccion(db: AsyncSession, operation: SyncOperation) -> str:
        data = dict(operation.payload)
        entity_id = data.get("id", operation.id)
        payload_updated_at = (
            parse_datetime(data.get("updated_at")) or operation.created_at
        )

        result = await db.execute(
            select(ProduccionHuevo).where(ProduccionHuevo.id == entity_id)
        )
        row = result.scalar_one_or_none()

        if row is None:
            required_fields = ["galpon_id", "fecha", "cantidad"]
            missing = [field for field in required_fields if field not in data]
            if missing:
                raise AppException(
                    message=f"Faltan campos requeridos: {', '.join(missing)}"
                )

            row = ProduccionHuevo(
                id=entity_id,
                galpon_id=data["galpon_id"],
                lote_id=data.get("lote_id"),
                fecha=parse_datetime(data["fecha"]),
                cantidad=int(data["cantidad"]),
                huevos_rotos=data.get("huevos_rotos"),
                observaciones=data.get("observaciones"),
            )
            db.add(row)
            return "Creado por sync"

        if SyncService._is_stale_update(row.updated_at, payload_updated_at):
            return LWW_DESCARTADO

        update_data = {
            "galpon_id": data.get("galpon_id", row.galpon_id),
            "lote_id": data.get("lote_id", row.lote_id),
            "fecha": parse_datetime(data.get("fecha")) or row.fecha,
            "cantidad": int(data.get("cantidad", row.cantidad)),
            "huevos_rotos": data.get("huevos_rotos", row.huevos_rotos),
            "observaciones": data.get("observaciones", row.observaciones),
        }
        update_model_from_dict(row, update_data)
        return "Actualizado por sync"

    @staticmethod
    async def _upsert_galpon(db: AsyncSession, operation: SyncOperation) -> str:
        data = dict(operation.payload)
        entity_id = data.get("id", operation.id)
        payload_updated_at = (
            parse_datetime(data.get("updated_at")) or operation.created_at
        )

        result = await db.execute(select(Galpon).where(Galpon.id == entity_id))
        row = result.scalar_one_or_none()

        if row is None:
            required_fields = ["nombre", "ubicacion", "capacidad", "propietario_id"]
            missing = [field for field in required_fields if field not in data]
            if missing:
                raise AppException(
                    message=f"Faltan campos requeridos: {', '.join(missing)}"
                )

            row = Galpon(
                id=entity_id,
                nombre=data["nombre"],
                ubicacion=data["ubicacion"],
                capacidad=int(data["capacidad"]),
                estado=EstadoGalpon(data.get("estado", EstadoGalpon.ACTIVO.value)),
                descripcion=data.get("descripcion"),
                propietario_id=data["propietario_id"],
            )
            db.add(row)
            return "Galpon creado por sync"

        if SyncService._is_stale_update(row.updated_at, payload_updated_at):
            return LWW_DESCARTADO

        update_data = {
            "nombre": data.get("nombre", row.nombre),
            "ubicacion": data.get("ubicacion", row.ubicacion),
            "capacidad": int(data.get("capacidad", row.capacidad)),
            "estado": EstadoGalpon(data.get("estado", row.estado.value)),
            "descripcion": data.get("descripcion", row.descripcion),
            "propietario_id": data.get("propietario_id", row.propietario_id),
        }
        update_model_from_dict(row, update_data)
        return "Galpon actualizado por sync"

    @staticmethod
    async def _upsert_lote(db: AsyncSession, operation: SyncOperation) -> str:
        data = dict(operation.payload)
        entity_id = data.get("id", operation.id)
        payload_updated_at = (
            parse_datetime(data.get("updated_at")) or operation.created_at
        )

        result = await db.execute(select(LoteAve).where(LoteAve.id == entity_id))
        row = result.scalar_one_or_none()

        if row is None:
            required_fields = [
                "codigo_lote",
                "tipo_ave",
                "raza",
                "cantidad_inicial",
                "fecha_ingreso",
                "galpon_id",
            ]
            missing = [field for field in required_fields if field not in data]
            if missing:
                raise AppException(
                    message=f"Faltan campos requeridos: {', '.join(missing)}"
                )

            cantidad_inicial = int(data["cantidad_inicial"])
            row = LoteAve(
                id=entity_id,
                codigo_lote=data["codigo_lote"],
                tipo_ave=data["tipo_ave"],
                raza=data["raza"],
                cantidad_inicial=cantidad_inicial,
                cantidad_actual=int(data.get("cantidad_actual", cantidad_inicial)),
                fecha_ingreso=parse_datetime(data["fecha_ingreso"]),
                galpon_id=data["galpon_id"],
                estado=EstadoLote(data.get("estado", EstadoLote.ACTIVO.value)),
            )
            db.add(row)
            return "Lote creado por sync"

        if SyncService._is_stale_update(row.updated_at, payload_updated_at):
            return LWW_DESCARTADO

        update_data = {
            "codigo_lote": data.get("codigo_lote", row.codigo_lote),
            "tipo_ave": data.get("tipo_ave", row.tipo_ave),
            "raza": data.get("raza", row.raza),
            "cantidad_inicial": int(data.get("cantidad_inicial", row.cantidad_inicial)),
            "cantidad_actual": int(data.get("cantidad_actual", row.cantidad_actual)),
            "fecha_ingreso": parse_datetime(data.get("fecha_ingreso"))
            or row.fecha_ingreso,
            "galpon_id": data.get("galpon_id", row.galpon_id),
            "estado": EstadoLote(data.get("estado", row.estado.value)),
        }
        update_model_from_dict(row, update_data)
        return "Lote actualizado por sync"

    @staticmethod
    async def _upsert_evento_sanitario(
        db: AsyncSession, operation: SyncOperation
    ) -> str:
        data = dict(operation.payload)
        entity_id = data.get("id", operation.id)
        payload_updated_at = (
            parse_datetime(data.get("updated_at")) or operation.created_at
        )

        result = await db.execute(
            select(EventoSanitario).where(EventoSanitario.id == entity_id)
        )
        row = result.scalar_one_or_none()

        if row is None:
            required_fields = [
                "lote_id",
                "galpon_id",
                "tipo_evento",
                "descripcion",
                "producto",
                "dosis",
                "responsable",
                "fecha",
            ]
            missing = [field for field in required_fields if field not in data]
            if missing:
                raise AppException(
                    message=f"Faltan campos requeridos: {', '.join(missing)}"
                )

            row = EventoSanitario(
                id=entity_id,
                lote_id=data["lote_id"],
                galpon_id=data["galpon_id"],
                tipo_evento=TipoEventoSanitario(data["tipo_evento"]),
                descripcion=data["descripcion"],
                producto=data["producto"],
                dosis=data["dosis"],
                responsable=data["responsable"],
                fecha=parse_datetime(data["fecha"]),
                observaciones=data.get("observaciones"),
            )
            db.add(row)
            return "Evento sanitario creado por sync"

        if SyncService._is_stale_update(row.updated_at, payload_updated_at):
            return LWW_DESCARTADO

        update_data = {
            "lote_id": data.get("lote_id", row.lote_id),
            "galpon_id": data.get("galpon_id", row.galpon_id),
            "tipo_evento": TipoEventoSanitario(
                data.get("tipo_evento", row.tipo_evento.value)
            ),
            "descripcion": data.get("descripcion", row.descripcion),
            "producto": data.get("producto", row.producto),
            "dosis": data.get("dosis", row.dosis),
            "responsable": data.get("responsable", row.responsable),
            "fecha": parse_datetime(data.get("fecha")) or row.fecha,
            "observaciones": data.get("observaciones", row.observaciones),
        }
        update_model_from_dict(row, update_data)
        return "Evento sanitario actualizado por sync"

    @staticmethod
    async def _upsert_alimentacion(db: AsyncSession, operation: SyncOperation) -> str:
        data = dict(operation.payload)
        entity_id = data.get("id", operation.id)
        payload_updated_at = (
            parse_datetime(data.get("updated_at")) or operation.created_at
        )

        result = await db.execute(
            select(AlimentacionRegistro).where(AlimentacionRegistro.id == entity_id)
        )
        row = result.scalar_one_or_none()

        if row is None:
            required_fields = ["galpon_id", "fecha", "tipo_alimento", "cantidad_kg"]
            missing = [field for field in required_fields if field not in data]
            if missing:
                raise AppException(
                    message=f"Faltan campos requeridos: {', '.join(missing)}"
                )

            row = AlimentacionRegistro(
                id=entity_id,
                galpon_id=data["galpon_id"],
                lote_id=data.get("lote_id"),
                fecha=parse_datetime(data["fecha"]),
                tipo_alimento=data["tipo_alimento"],
                cantidad_kg=float(data["cantidad_kg"]),
                costo=float(data["costo"]) if data.get("costo") is not None else None,
                observaciones=data.get("observaciones"),
            )
            db.add(row)
            return "Alimentacion creada por sync"

        if SyncService._is_stale_update(row.updated_at, payload_updated_at):
            return LWW_DESCARTADO

        update_data = {
            "galpon_id": data.get("galpon_id", row.galpon_id),
            "lote_id": data.get("lote_id", row.lote_id),
            "fecha": parse_datetime(data.get("fecha")) or row.fecha,
            "tipo_alimento": data.get("tipo_alimento", row.tipo_alimento),
            "cantidad_kg": float(data.get("cantidad_kg", row.cantidad_kg)),
            "costo": (
                float(data["costo"]) if data.get("costo") is not None else row.costo
            ),
            "observaciones": data.get("observaciones", row.observaciones),
        }
        update_model_from_dict(row, update_data)
        return "Alimentacion actualizada por sync"

    @staticmethod
    async def _upsert_movimiento(db: AsyncSession, operation: SyncOperation) -> str:
        data = dict(operation.payload)
        entity_id = data.get("id", operation.id)
        payload_updated_at = (
            parse_datetime(data.get("updated_at")) or operation.created_at
        )

        result = await db.execute(
            select(MovimientoAve).where(MovimientoAve.id == entity_id)
        )
        row = result.scalar_one_or_none()

        if row is None:
            return await SyncService._crear_movimiento(db, entity_id, data)

        if SyncService._is_stale_update(row.updated_at, payload_updated_at):
            return LWW_DESCARTADO

        update_data = {
            "tipo_movimiento": TipoMovimientoAve(
                data.get("tipo_movimiento", row.tipo_movimiento.value)
            ),
            "cantidad": int(data.get("cantidad", row.cantidad)),
            "causa": data.get("causa", row.causa),
            "fecha": parse_datetime(data.get("fecha")) or row.fecha,
            "observaciones": data.get("observaciones", row.observaciones),
        }
        update_model_from_dict(row, update_data)
        return "Movimiento actualizado por sync"
