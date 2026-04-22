# CORRECCIÓN APLICADA: Reportes S3
import asyncio
import logging
import os
import re
import tempfile
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from fastapi import status
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.reportes.models import ReporteGenerado
from app.modules.reportes.schemas import ReporteGenerarRequest, ReporteOut

logger = logging.getLogger(__name__)


class ReportesService:
    @staticmethod
    def _sanitize_payload_names(payload: ReporteGenerarRequest) -> tuple[int, str, str]:
        timestamp = int(datetime.now(timezone.utc).timestamp())
        tipo_safe = re.sub(r"[^a-zA-Z0-9_-]", "_", payload.tipo)
        formato_safe = re.sub(r"[^a-zA-Z0-9]", "", payload.formato).lower()
        return timestamp, tipo_safe, formato_safe

    @staticmethod
    def _create_temp_pdf_path(tipo_safe: str, timestamp: int) -> str:
        fd, ruta = tempfile.mkstemp(
            suffix=".pdf",
            prefix=f"reporte_{tipo_safe}_{timestamp}_",
        )
        os.close(fd)
        return ruta

    @staticmethod
    def _build_pdf(payload: ReporteGenerarRequest, ruta_tmp: str) -> None:
        pdf = canvas.Canvas(ruta_tmp, pagesize=A4)
        pdf.setTitle(f"Reporte {payload.tipo}")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(72, 800, f"Reporte {payload.tipo}")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(
            72,
            770,
            f"Período: {payload.fecha_inicio.date()} — {payload.fecha_fin.date()}",
        )
        pdf.drawString(
            72,
            740,
            (
                "Generado: "
                f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
            ),
        )
        pdf.save()

    @staticmethod
    def _build_s3_params(s3_key: str) -> tuple[dict[str, str] | None, dict[str, str]]:
        extra_args: dict[str, str] = {}
        if settings.aws_s3_expected_bucket_owner:
            extra_args["ExpectedBucketOwner"] = settings.aws_s3_expected_bucket_owner

        params = {
            "Bucket": settings.aws_s3_bucket,
            "Key": s3_key,
        }
        if settings.aws_s3_expected_bucket_owner:
            params["ExpectedBucketOwner"] = settings.aws_s3_expected_bucket_owner

        return (extra_args or None), params

    @staticmethod
    def _upload_pdf_to_s3(ruta_tmp: str, s3_key: str) -> str:
        s3 = boto3.client(
            "s3",
            region_name=settings.aws_region,
        )
        extra_args, params = ReportesService._build_s3_params(s3_key)
        s3.upload_file(
            ruta_tmp,
            settings.aws_s3_bucket,
            s3_key,
            ExtraArgs=extra_args,
        )
        return s3.generate_presigned_url(
            "get_object",
            Params=params,
            ExpiresIn=86400,
        )

    @staticmethod
    async def _persist_report_file(
        payload: ReporteGenerarRequest,
        timestamp: int,
        tipo_safe: str,
    ) -> str:
        ruta_tmp = await asyncio.to_thread(
            ReportesService._create_temp_pdf_path,
            tipo_safe,
            timestamp,
        )
        await asyncio.to_thread(ReportesService._build_pdf, payload, ruta_tmp)

        if settings.environment != "production" or not settings.aws_s3_bucket:
            return ruta_tmp

        s3_key = f"reportes/{tipo_safe}_{timestamp}.pdf"
        try:
            url = await asyncio.to_thread(ReportesService._upload_pdf_to_s3, ruta_tmp, s3_key)
            try:
                os.unlink(ruta_tmp)
            except OSError:
                pass
            return url
        except ClientError as exc:
            logger.error("Error al subir reporte a S3: %s", exc)
            return ruta_tmp

    @staticmethod
    async def list(db: AsyncSession) -> list[ReporteOut]:
        result = await db.execute(
            select(ReporteGenerado)
            .where(ReporteGenerado.deleted_at.is_(None))
            .order_by(ReporteGenerado.created_at.desc())
        )
        return [ReporteOut.model_validate(item) for item in result.scalars().all()]

    @staticmethod
    async def get_by_id(db: AsyncSession, reporte_id: str) -> ReporteOut:
        result = await db.execute(
            select(ReporteGenerado).where(
                ReporteGenerado.id == reporte_id,
                ReporteGenerado.deleted_at.is_(None),
            )
        )
        reporte = result.scalar_one_or_none()
        if reporte is None:
            raise AppException(
                message="Reporte no encontrado",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return ReporteOut.model_validate(reporte)

    @staticmethod
    async def generar(db: AsyncSession, payload: ReporteGenerarRequest) -> ReporteOut:
        timestamp, tipo_safe, formato_safe = ReportesService._sanitize_payload_names(
            payload
        )

        url_archivo = f"/reportes/{tipo_safe}_{timestamp}.{formato_safe}"
        if payload.formato.upper() == "PDF":
            url_archivo = await ReportesService._persist_report_file(
                payload,
                timestamp,
                tipo_safe,
            )

        reporte = ReporteGenerado(
            tipo=payload.tipo,
            fecha_inicio=payload.fecha_inicio,
            fecha_fin=payload.fecha_fin,
            formato=payload.formato,
            url_archivo=url_archivo,
            generado_por=payload.generado_por,
        )

        db.add(reporte)
        await db.commit()
        await db.refresh(reporte)
        return ReporteOut.model_validate(reporte)
