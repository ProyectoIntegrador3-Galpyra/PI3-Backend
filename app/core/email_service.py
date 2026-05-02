from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


def _get_mail_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.smtp_user,
        MAIL_PASSWORD=settings.smtp_password,
        MAIL_FROM=settings.smtp_from or settings.smtp_user,
        MAIL_PORT=settings.smtp_port,
        MAIL_SERVER=settings.smtp_host,
        MAIL_FROM_NAME=settings.smtp_from_name,
        MAIL_STARTTLS=True,
        MAIL_SSL_TLS=False,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


def _build_reset_html(token: str, nombre: str) -> str:
    reset_link = f"{settings.frontend_url}/{token}"
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <body style="margin:0;padding:0;background:#FFF8E7;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0"
             style="background:#FFF8E7;padding:40px 0;">
        <tr><td align="center">
          <table width="480" cellpadding="0" cellspacing="0"
                 style="background:#ffffff;border-radius:16px;overflow:hidden;">
            <tr>
              <td style="background:#D4920A;padding:32px 40px;text-align:center;">
                <p style="margin:0;font-size:28px;">🥚</p>
                <h1 style="margin:8px 0 0;color:#ffffff;font-size:22px;">GALPyra</h1>
                <p style="margin:4px 0 0;color:#FFF3CC;font-size:13px;">
                  Gestión Avícola y Trazabilidad Productiva
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:40px;">
                <h2 style="margin:0 0 16px;color:#1A1A1A;font-size:20px;">
                  Hola, {nombre} 👋
                </h2>
                <p style="margin:0 0 16px;color:#4A4A4A;font-size:15px;line-height:1.6;">
                  Recibimos una solicitud para restablecer la contraseña
                  de tu cuenta GALPyra.
                </p>
                <p style="margin:0 0 28px;color:#4A4A4A;font-size:15px;line-height:1.6;">
                  Este enlace <strong>expira en 15 minutos</strong>.
                </p>
                <table width="100%"><tr><td align="center">
                  <a href="{reset_link}"
                     style="display:inline-block;background:#D4920A;
                            color:#ffffff;text-decoration:none;
                            font-size:16px;font-weight:700;
                            padding:16px 40px;border-radius:12px;">
                    Restablecer contraseña
                  </a>
                </td></tr></table>
                <p style="margin:28px 0 0;color:#888888;font-size:13px;">
                  Si no solicitaste este cambio, ignora este correo.
                </p>
                <p style="margin:12px 0 0;color:#BBBBBB;font-size:12px;">
                  O copia este enlace:<br>
                  <span style="color:#D4920A;word-break:break-all;">
                    {reset_link}
                  </span>
                </p>
              </td>
            </tr>
            <tr>
              <td style="background:#FFF8E7;padding:20px 40px;
                         text-align:center;border-top:1px solid #E8D5A3;">
                <p style="margin:0;color:#999999;font-size:12px;">
                  GALPyra · Universidad Pontificia Bolivariana<br>
                  Bucaramanga, Santander, Colombia
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


async def send_password_reset_email(
    email_to: str,
    nombre: str,
    token: str,
) -> bool:
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning(
            "SMTP no configurado. Email NO enviado a %s. Token: %s",
            email_to,
            token,
        )
        return False
    try:
        conf = _get_mail_config()
        fm = FastMail(conf)
        message = MessageSchema(
            subject="Recupera tu contraseña — GALPyra",
            recipients=[email_to],
            body=_build_reset_html(token, nombre),
            subtype=MessageType.html,
        )
        await fm.send_message(message)
        logger.info("Email de recuperación enviado a %s", email_to)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Error enviando email a %s: %s", email_to, type(exc).__name__)
        return False
