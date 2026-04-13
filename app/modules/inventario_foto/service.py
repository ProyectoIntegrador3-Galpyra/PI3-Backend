import logging
import hashlib
import struct
from collections import deque
from datetime import datetime, timezone
from time import perf_counter
from pathlib import Path
from uuid import uuid4

logger = logging.getLogger(__name__)
_YOLO_MODEL = None
_YOLO_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "yolov8n.pt"
_BIRD_CLASS_ID = 14
_RECENT_COUNTS: deque[tuple[datetime, int]] = deque()
_COUNT_WINDOW_MINUTES = 15
_COUNT_ALERT_RATIO = 0.6


def _load_yolo_model_once():
    global _YOLO_MODEL
    if _YOLO_MODEL is not None:
        return _YOLO_MODEL
    logger.info(
        "YOLO model path: %s exists=%s size=%s",
        _YOLO_MODEL_PATH,
        _YOLO_MODEL_PATH.exists(),
        _YOLO_MODEL_PATH.stat().st_size if _YOLO_MODEL_PATH.exists() else 0,
    )
    if not _YOLO_MODEL_PATH.exists() or _YOLO_MODEL_PATH.stat().st_size <= 1024:
        return None

    try:
        from ultralytics import YOLO  # type: ignore

        _YOLO_MODEL = YOLO(str(_YOLO_MODEL_PATH))
    except Exception as exc:  # noqa: BLE001
        logger.exception("No fue posible cargar YOLOv8n al iniciar")
        _YOLO_MODEL = None
    return _YOLO_MODEL


_load_yolo_model_once()


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_GIF_SIGNATURES = (b"GIF87a", b"GIF89a")
_JPEG_SOI = b"\xff\xd8"
_JPEG_SOF_MARKERS = {
    0xC0,
    0xC1,
    0xC2,
    0xC3,
    0xC5,
    0xC6,
    0xC7,
    0xC9,
    0xCA,
    0xCB,
    0xCD,
    0xCE,
    0xCF,
}


def _extract_image_metadata(image_bytes: bytes) -> tuple[str, int, int]:
    if image_bytes.startswith(_PNG_SIGNATURE):
        if len(image_bytes) < 24:
            raise AppException(
                message="La imagen PNG está incompleta",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        width = struct.unpack(">I", image_bytes[16:20])[0]
        height = struct.unpack(">I", image_bytes[20:24])[0]
        return "png", width, height

    if image_bytes.startswith(_GIF_SIGNATURES):
        if len(image_bytes) < 10:
            raise AppException(
                message="La imagen GIF está incompleta",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        width = struct.unpack("<H", image_bytes[6:8])[0]
        height = struct.unpack("<H", image_bytes[8:10])[0]
        return "gif", width, height

    if image_bytes.startswith(_JPEG_SOI):
        offset = 2
        while offset < len(image_bytes):
            if image_bytes[offset] != 0xFF:
                offset += 1
                continue

            while offset < len(image_bytes) and image_bytes[offset] == 0xFF:
                offset += 1

            if offset >= len(image_bytes):
                break

            marker = image_bytes[offset]
            offset += 1

            if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
                continue

            if offset + 2 > len(image_bytes):
                break

            segment_length = struct.unpack(">H", image_bytes[offset : offset + 2])[0]
            if segment_length < 2:
                break

            segment_start = offset + 2
            if marker in _JPEG_SOF_MARKERS:
                if segment_start + 5 >= len(image_bytes):
                    break
                height = struct.unpack(
                    ">H", image_bytes[segment_start + 1 : segment_start + 3]
                )[0]
                width = struct.unpack(
                    ">H", image_bytes[segment_start + 3 : segment_start + 5]
                )[0]
                return "jpeg", width, height

            offset += segment_length

        raise AppException(
            message="No fue posible leer las dimensiones de la imagen JPEG",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    raise AppException(
        message="El archivo enviado no parece ser una imagen PNG, GIF o JPEG válida",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


def _estimate_mock_count(image_bytes: bytes, width: int, height: int) -> int:
    digest = hashlib.sha256(image_bytes).digest()
    seed = int.from_bytes(digest[:4], "big")
    scale = max(1, (width * height) // 256)
    return max(1, ((seed % 97) + width + height + scale) % 120 + 1)


def _record_recent_count(conteo: int, request_id: str, source: str) -> None:
    now = datetime.now(timezone.utc)
    _RECENT_COUNTS.append((now, conteo))

    threshold = now.timestamp() - (_COUNT_WINDOW_MINUTES * 60)
    while _RECENT_COUNTS and _RECENT_COUNTS[0][0].timestamp() < threshold:
        _RECENT_COUNTS.popleft()

    if len(_RECENT_COUNTS) < 3:
        return

    same_count = sum(1 for _, value in _RECENT_COUNTS if value == conteo)
    ratio = same_count / len(_RECENT_COUNTS)
    if ratio > _COUNT_ALERT_RATIO:
        logger.warning(
            "inventario_foto_count_distribution_alert request_id=%s source=%s conteo=%s repeat_ratio=%.2f window_size=%s",
            request_id,
            source,
            conteo,
            ratio,
            len(_RECENT_COUNTS),
        )

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.inventario_foto.models import InventarioFotoJob
from app.modules.inventario_foto.schemas import (
    InventarioConfirmarRequest,
    InventarioFotoJobOut,
    InventarioProcesarResponse,
)
from app.shared.enums import EstadoInventarioFoto


class InventarioFotoService:
    @staticmethod
    async def procesar_imagen(
        db: AsyncSession,
        file: UploadFile,
        lote_id: str | None,
        galpon_id: str | None,
    ) -> InventarioProcesarResponse:
        request_id = str(uuid4())
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{request_id}_{file.filename or 'inventario.jpg'}"
        file_path = upload_dir / safe_filename
        started_at = perf_counter()

        image_bytes = await file.read()
        if not image_bytes:
            raise AppException(
                message="La imagen está vacía",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        image_format, image_width, image_height = _extract_image_metadata(image_bytes)

        with file_path.open("wb") as out_file:
            out_file.write(image_bytes)

        conteo: int | None = None
        bounding_boxes: list[dict] = []
        modo = "model"
        source = "model"
        warning: str | None = None
        confidence_avg: float | None = None

        try:
            model = _load_yolo_model_once()
            if model is not None:
                try:
                    results = model.predict(source=str(file_path), verbose=False)
                except Exception as predict_exc:  # noqa: BLE001
                    logger.warning(
                        "inventario_foto_predict_error request_id=%s filename=%s error=%s",
                        request_id,
                        file.filename or safe_filename,
                        predict_exc,
                    )
                    results = []
                if results:
                    boxes = results[0].boxes
                    detecciones_bird: list = []
                    for box in boxes:
                        box_cls = getattr(box, "cls", None)
                        if box_cls is None:
                            detecciones_bird.append(box)
                            continue
                        try:
                            cls_value = int(float(box_cls.item()))
                        except Exception:  # noqa: BLE001
                            try:
                                cls_value = int(float(box_cls.tolist()[0]))
                            except Exception:  # noqa: BLE001
                                cls_value = -1

                        if cls_value == _BIRD_CLASS_ID:
                            detecciones_bird.append(box)

                    conteo = len(detecciones_bird)
                    bounding_boxes = []
                    confidences: list[float] = []
                    for box in detecciones_bird:
                        xyxy = box.xyxy.tolist()[0]
                        bounding_boxes.append(
                            {
                                "x1": float(xyxy[0]),
                                "y1": float(xyxy[1]),
                                "x2": float(xyxy[2]),
                                "y2": float(xyxy[3]),
                            }
                        )
                        box_conf = getattr(box, "conf", None)
                        if box_conf is not None:
                            try:
                                confidences.append(float(box_conf.item()))
                            except Exception:  # noqa: BLE001
                                try:
                                    confidences.append(float(box_conf.tolist()[0]))
                                except Exception:  # noqa: BLE001
                                    pass

                    if confidences:
                        confidence_avg = sum(confidences) / len(confidences)
                else:
                    conteo = 0

                if conteo is None:
                    conteo = len(bounding_boxes)
            else:
                if settings.environment == "production":
                    raise AppException(
                        message="Modelo de inventario no disponible en producción",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                if not settings.yolo_mock:
                    raise AppException(
                        message=(
                            "Modelo de inventario no disponible y fallback mock deshabilitado"
                        ),
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )

                conteo = _estimate_mock_count(image_bytes, image_width, image_height)
                bounding_boxes = []
                modo = "mock"
                source = "mock"
                warning = "resultado_no_confiable"
        except Exception as exc:  # noqa: BLE001
            if isinstance(exc, AppException):
                raise

            logger.warning(
                "inventario_foto_inference_error request_id=%s filename=%s error=%s",
                request_id,
                file.filename or safe_filename,
                exc,
            )

            if settings.environment == "production" or not settings.yolo_mock:
                raise AppException(
                    message="No fue posible procesar la imagen con el modelo de inventario",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                ) from exc

            conteo = _estimate_mock_count(image_bytes, image_width, image_height)
            bounding_boxes = []
            modo = "mock"
            source = "mock"
            warning = "resultado_no_confiable"

        inference_ms = (perf_counter() - started_at) * 1000

        _record_recent_count(conteo or 0, request_id, source)
        logger.info(
            (
                "inventario_foto_request request_id=%s filename=%s size_bytes=%s "
                "dimensions=%sx%s format=%s inference_ms=%.2f detections=%s "
                "confidence_avg=%s source=%s"
            ),
            request_id,
            file.filename or safe_filename,
            len(image_bytes),
            image_width,
            image_height,
            image_format,
            inference_ms,
            conteo,
            f"{confidence_avg:.4f}" if confidence_avg is not None else "n/a",
            source,
        )

        job = InventarioFotoJob(
            lote_id=lote_id,
            galpon_id=galpon_id,
            image_url=str(file_path).replace("\\", "/"),
            filename=safe_filename,
            conteo_estimado=conteo,
            origen=source,
            estado=EstadoInventarioFoto.PROCESADO,
            bounding_boxes_json=bounding_boxes,
            procesado_en=datetime.now(timezone.utc),
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        return InventarioProcesarResponse(
            conteo=conteo,
            bounding_boxes=bounding_boxes,
            job_id=job.id,
            modo=modo,
            source=source,
            request_id=request_id,
            warning=warning,
        )

    @staticmethod
    async def confirmar_conteo(
        db: AsyncSession,
        payload: InventarioConfirmarRequest,
    ) -> InventarioFotoJobOut:
        result = await db.execute(
            select(InventarioFotoJob).where(
                InventarioFotoJob.id == payload.job_id,
                InventarioFotoJob.deleted_at.is_(None),
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise AppException(
                message="Job de inventario no encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        job.conteo_confirmado = payload.conteo_confirmado
        job.lote_id = payload.lote_id or job.lote_id
        job.galpon_id = payload.galpon_id or job.galpon_id
        job.estado = EstadoInventarioFoto.CONFIRMADO
        job.confirmado_en = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        return InventarioFotoJobOut.model_validate(job)

    @staticmethod
    async def list_jobs(db: AsyncSession) -> list[InventarioFotoJobOut]:
        result = await db.execute(
            select(InventarioFotoJob)
            .where(InventarioFotoJob.deleted_at.is_(None))
            .order_by(InventarioFotoJob.created_at.desc())
        )
        return [
            InventarioFotoJobOut.model_validate(item) for item in result.scalars().all()
        ]

    @staticmethod
    async def get_job(db: AsyncSession, job_id: str) -> InventarioFotoJobOut:
        result = await db.execute(
            select(InventarioFotoJob).where(
                InventarioFotoJob.id == job_id,
                InventarioFotoJob.deleted_at.is_(None),
            )
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise AppException(
                message="Job de inventario no encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return InventarioFotoJobOut.model_validate(job)
