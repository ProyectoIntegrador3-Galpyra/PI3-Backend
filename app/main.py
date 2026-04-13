from collections import defaultdict, deque
from time import monotonic

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.responses import error_response, success_response
from app.modules.alimentacion.router import router as alimentacion_router
from app.modules.auth.router import router as auth_router
from app.modules.aves.router import router as aves_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.galpones.router import router as galpones_router
from app.modules.inventario_foto.router import router as inventario_router
from app.modules.produccion.router import router as produccion_router
from app.modules.reportes.router import router as reportes_router
from app.modules.sanidad.router import router as sanidad_router
from app.modules.sync.router import router as sync_router
from app.modules.trazabilidad.router import router as trazabilidad_router


def _resolve_cors_origins() -> list[str]:
    cors_origins = [
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    ]
    if not cors_origins:
        cors_origins = ["*"]

    if settings.environment == "production" and "*" in cors_origins:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS no puede contener '*' en produccion"
        )

    return cors_origins


def _build_rate_limit_middleware_state() -> tuple[dict[str, int], int, dict[tuple[str, str], deque[float]]]:
    rules = {
        "/api/auth/login": settings.auth_login_rate_limit,
        "/api/sync": settings.sync_rate_limit,
    }
    window = settings.rate_limit_window_seconds
    history: dict[tuple[str, str], deque[float]] = defaultdict(deque)
    return rules, window, history


def _set_security_headers(response, path: str) -> None:
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    # Swagger UI/ReDoc inject inline scripts/styles that are blocked by strict CSP.
    # Keep CSP on app/API routes and skip it only on documentation endpoints.
    if path not in {"/docs", "/redoc", "/openapi.json"}:
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )


def create_app() -> FastAPI:
    app = FastAPI(
        title="GALPyra API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    cors_origins = _resolve_cors_origins()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    rate_limit_rules, rate_limit_window, request_history = (
        _build_rate_limit_middleware_state()
    )

    @app.middleware("http")
    async def security_middleware(request, call_next):
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        if settings.rate_limit_enabled and path in rate_limit_rules:
            now = monotonic()
            history = request_history[(client_ip, path)]

            while history and (now - history[0]) > rate_limit_window:
                history.popleft()

            if len(history) >= rate_limit_rules[path]:
                return JSONResponse(
                    status_code=429,
                    content=error_response(
                        message="Demasiadas solicitudes, intenta de nuevo en unos segundos",
                        error="rate_limit_exceeded",
                        status_code=429,
                    ),
                )

            history.append(now)

        response = await call_next(request)
        _set_security_headers(response, path)

        return response

    api_router = APIRouter(prefix="/api")

    @api_router.get("/health", tags=["Health"])
    async def health() -> dict:
        return success_response(
            message="Servicio saludable",
            data={"status": "ok", "environment": settings.environment},
        )

    api_router.include_router(auth_router)
    api_router.include_router(galpones_router)
    api_router.include_router(aves_router)
    api_router.include_router(produccion_router)
    api_router.include_router(sanidad_router)
    api_router.include_router(alimentacion_router)
    api_router.include_router(reportes_router)
    api_router.include_router(sync_router)
    api_router.include_router(inventario_router)
    api_router.include_router(dashboard_router)
    api_router.include_router(trazabilidad_router)

    app.include_router(api_router)
    register_exception_handlers(app)

    return app


app = create_app()
