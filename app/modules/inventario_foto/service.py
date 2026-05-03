import hashlib
import logging
import struct
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import boto3

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.inventario_foto.models import InventarioFotoJob
from app.modules.inventario_foto.schemas import (
    ConfirmarInventarioResponse,
    InventarioConfirmarRequest,
    InventarioFotoJobOut,
    InventarioProcesarResponse,
)
from app.shared.enums import EstadoInventarioFoto
from app.modules.aves.models import LoteAve

logger = logging.getLogger(__name__)
_YOLO_MODEL = None
_YOLO_MODEL_PATH = Path(__file__).resolve().parent.parent.parent.parent / "models" / "yolov8n.pt"
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
    except Exception:  # noqa: BLE001
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


def _is_jpeg_standalone_marker(marker: int) -> bool:
    return marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7


def _read_jpeg_sof_dimensions(image_bytes: bytes, segment_start: int) -> tuple[int, int] | None:
    if segment_start + 5 >= len(image_bytes):
        return None
    height = struct.unpack(">H", image_bytes[segment_start + 1 : segment_start + 3])[0]
    width = struct.unpack(">H", image_bytes[segment_start + 3 : segment_start + 5])[0]
    return width, height


def _read_jpeg_dimensions(image_bytes: bytes) -> tuple[int, int] | None:
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
        if _is_jpeg_standalone_marker(marker):
            continue
        if offset + 2 > len(image_bytes):
            break
        segment_length = struct.unpack(">H", image_bytes[offset : offset + 2])[0]
        if segment_length < 2:
            break
        if marker in _JPEG_SOF_MARKERS:
            return _read_jpeg_sof_dimensions(image_bytes, offset + 2)
        offset += segment_length
    return None


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
        dims = _read_jpeg_dimensions(image_bytes)
        if dims is None:
            raise AppException(
                message="No fue posible leer las dimensiones de la imagen JPEG",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return "jpeg", dims[0], dims[1]

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
            "inventario_foto_count_distribution_alert request_id=%s source=%s "
            "conteo=%s repeat_ratio=%.2f window_size=%s",
            request_id,
            source,
            conteo,
            ratio,
            len(_RECENT_COUNTS),
        )


def _get_box_cls(box) -> int:
    box_cls = getattr(box, "cls", None)
    if box_cls is None:
        return _BIRD_CLASS_ID
    try:
        return int(float(box_cls.item()))
    except Exception:  # noqa: BLE001
        try:
            return int(float(box_cls.tolist()[0]))
        except Exception:  # noqa: BLE001
            return -1


def _get_box_confidence(box) -> float | None:
    box_conf = getattr(box, "conf", None)
    if box_conf is None:
        return None
    try:
        return float(box_conf.item())
    except Exception:  # noqa: BLE001
        try:
            return float(box_conf.tolist()[0])
        except Exception:  # noqa: BLE001
            return None


def _process_yolo_results(
    results: list,
    image_width: int,
    image_height: int,
) -> tuple[int, list[dict], float | None]:
    if not results:
        return 0, [], None

    boxes = results[0].boxes
    if boxes is None:
        return 0, [], None

    image_area = max(1.0, float(image_width * image_height))
    min_area_ratio = settings.yolo_min_box_area_ratio

    bounding_boxes: list[dict] = []
    confidences: list[float] = []
    for box in boxes:
        if _get_box_cls(box) != _BIRD_CLASS_ID:
            continue

        conf = _get_box_confidence(box)
        if conf is None or conf < settings.yolo_conf_threshold:
            continue

        xyxy = box.xyxy.tolist()[0]
        width = max(0.0, float(xyxy[2]) - float(xyxy[0]))
        height = max(0.0, float(xyxy[3]) - float(xyxy[1]))
        area_ratio = (width * height) / image_area
        if area_ratio < min_area_ratio:
            continue

        bounding_boxes.append(
            {
                "x1": float(xyxy[0]),
                "y1": float(xyxy[1]),
                "x2": float(xyxy[2]),
                "y2": float(xyxy[3]),
            }
        )
        confidences.append(conf)

    confidence_avg = sum(confidences) / len(confidences) if confidences else None
    return len(bounding_boxes), bounding_boxes, confidence_avg


def _run_yolo_inference(model, file_path: Path, request_id: str) -> list:
    try:
        return model.predict(
            source=str(file_path),
            verbose=False,
            conf=settings.yolo_conf_threshold,
            iou=settings.yolo_iou_threshold,
            classes=[_BIRD_CLASS_ID],
            max_det=settings.yolo_max_det,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "inventario_foto_predict_error request_id=%s error=%s",
            request_id,
            type(exc).__name__,
        )
        return []


def _mock_fallback(
    image_bytes: bytes,
    image_width: int,
    image_height: int,
) -> tuple[int, list[dict], None, str, str, str]:
    if not settings.yolo_mock:
        raise AppException(
            message="Modelo de inventario no disponible",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    conteo = _estimate_mock_count(image_bytes, image_width, image_height)
    return conteo, [], None, "mock", "mock", "resultado_no_confiable"


def _infer_conteo(
    image_bytes: bytes,
    image_width: int,
    image_height: int,
    file_path: Path,
    request_id: str,
) -> tuple[int, list[dict], float | None, str, str, str | None]:
    try:
        model = _load_yolo_model_once()
        if model is not None:
            results = _run_yolo_inference(model, file_path, request_id)
            conteo, bounding_boxes, confidence_avg = _process_yolo_results(
                results,
                image_width,
                image_height,
            )
            return conteo, bounding_boxes, confidence_avg, "model", "model", None
        return _mock_fallback(image_bytes, image_width, image_height)
    except AppException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "inventario_foto_inference_error request_id=%s error=%s",
            request_id,
            type(exc).__name__,
        )
        if not settings.yolo_mock:
            raise AppException(
                message="No fue posible procesar la imagen con el modelo de inventario",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            ) from exc
        conteo = _estimate_mock_count(image_bytes, image_width, image_height)
        return conteo, [], None, "mock", "mock", "resultado_no_confiable"


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

        conteo, bounding_boxes, confidence_avg, modo, source, warning = _infer_conteo(
            image_bytes, image_width, image_height, file_path, request_id
        )

        inference_ms = (perf_counter() - started_at) * 1000
        _record_recent_count(conteo, request_id, source)
        logger.info(
            "inventario_foto_request request_id=%s size_bytes=%s dimensions=%sx%s "
            "format=%s inference_ms=%.2f detections=%s confidence_avg=%s source=%s",
            request_id,
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
    ) -> "ConfirmarInventarioResponse":
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

        # Actualizar cantidad_actual del lote si hay lote_id
        if job.lote_id:
            lote_result = await db.execute(
                select(LoteAve).where(
                    LoteAve.id == job.lote_id,
                    LoteAve.deleted_at.is_(None),
                )
            )
            lote = lote_result.scalar_one_or_none()
            if lote is not None:
                lote.cantidad_actual = payload.conteo_confirmado
                lote.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(job)

        # Guardar imagen en S3 (no fallar el endpoint si S3 falla)
        if job.image_url and settings.aws_s3_bucket:
            try:
                await InventarioFotoService._upload_image_to_s3(
                    job.image_url,
                    job.lote_id or job.galpon_id,
                    job.id,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "inventario_foto_s3_upload_error job_id=%s error=%s",
                    job.id,
                    type(exc).__name__,
                )

        return InventarioFotoJobOut.model_validate(job)

    @staticmethod
    async def _upload_image_to_s3(
        local_image_path: str,
        scope_id: str | None,
        job_id: str,
    ) -> None:
        """Carga la imagen procesada a S3 para archivo histórico."""
        if not all(
            [
                settings.aws_s3_bucket,
                settings.aws_access_key_id,
                settings.aws_secret_access_key,
                settings.aws_region,
            ]
        ):
            return

        try:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )

            local_path = Path(local_image_path)
            if not local_path.exists():
                logger.warning("Local image not found: %s", local_image_path)
                return

            s3_key = f"inventario/{scope_id}/{job_id}.jpg"

            with open(local_path, "rb") as image_file:
                s3_client.put_object(
                    Bucket=settings.aws_s3_bucket,
                    Key=s3_key,
                    Body=image_file.read(),
                    ContentType="image/jpeg",
                    ExpectedBucketOwner=settings.aws_s3_expected_bucket_owner,
                )

            logger.info("Image uploaded to S3: s3://%s/%s", settings.aws_s3_bucket, s3_key)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Failed to upload image to S3: %s",
                str(exc),
            )
            raise

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
