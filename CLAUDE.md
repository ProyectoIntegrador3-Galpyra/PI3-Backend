# CLAUDE.md — GALPyra Backend

> Guía de contexto para agentes de IA trabajando en el backend de **GALPyra**.
> Leer completo antes de generar código, modificar archivos o proponer cambios arquitectónicos.

---

## 1. Qué es este proyecto

**GALPyra** (Gestión Avícola y Trazabilidad Productiva) es una aplicación móvil offline-first para pequeños y medianos productores de huevo en Santander, Colombia. Este repositorio contiene únicamente el **backend**: una API REST en Python/FastAPI que actúa como capa intermedia entre la app Flutter y la base de datos MySQL en AWS RDS.

- **Institución:** Universidad Pontificia Bolivariana — Bucaramanga (Proyecto Integrador III)
- **Tutor:** Omar Pinzón Ardila
- **Equipo:** Zarhet Valentina Fuentes Botia · María Angélica Parra Grazt · Juan Carlos Niño Osorio

---

## 2. Stack tecnológico

| Tecnología | Versión | Rol |
|---|---|---|
| Python | 3.11+ | Lenguaje principal |
| FastAPI | 0.110+ | Framework web async + OpenAPI automático |
| SQLAlchemy | 2.0+ async | ORM para MySQL |
| aiomysql | latest | Driver async MySQL |
| Pydantic | v2 | Validación y serialización (schemas) |
| python-jose | 3.3+ | Generación y verificación de tokens JWT |
| passlib + bcrypt | latest | Hash de contraseñas (12 rondas) |
| pydantic-settings | 2.0+ | Lectura de variables de entorno |
| Alembic | latest | Migraciones de BD versionadas |
| pytest + httpx | latest | Tests unitarios e integración |
| uvicorn | latest | Servidor ASGI (producción) |
| ultralytics (YOLOv8n) | latest | Conteo automatizado de aves por foto |

---

## 3. Arquitectura

El backend es un **monolito modular** con bounded contexts por dominio funcional. No hay microservicios. Cada módulo bajo `app/modules/` es autocontenido y expone exactamente cuatro archivos: `router.py`, `service.py`, `schemas.py`, `models.py`.

```
Capa externa (internet)
        │  HTTPS :443
        ▼
AWS Elastic Beanstalk (EC2 t3.micro)
  └── FastAPI / uvicorn
        │  Routers → Services → Models (SQLAlchemy)
        ▼
AWS RDS MySQL 8.0 (puerto 3306, acceso solo desde SG de Beanstalk)
```

No hay lógica de negocio en los routers. No hay SQL crudo fuera de los modelos SQLAlchemy. Los servicios orquestan, los modelos persisten.

---

## 4. Estructura de directorios

```
galpyra-backend/
├── application.py              # Punto de entrada AWS Beanstalk
├── requirements.txt
├── .ebextensions/
│   └── python.config           # WSGIPath + InstanceType t3.micro
├── alembic/
│   ├── versions/
│   └── env.py
└── app/
    ├── main.py                 # App FastAPI + registro de todos los routers
    ├── core/
    │   ├── config.py           # Settings (pydantic-settings, lee vars de entorno)
    │   ├── database.py         # Engine async + AsyncSessionLocal + pool config
    │   ├── security.py         # create_access_token(), verify_token(), hash utils
    │   └── dependencies.py     # get_db(), get_current_user() (Depends)
    └── modules/
        ├── auth/
        │   ├── router.py       # POST /api/auth/login|refresh|logout, GET /api/auth/me
        │   ├── service.py
        │   ├── schemas.py      # LoginRequest, TokenResponse, UserOut
        │   └── models.py       # Usuario (SQLAlchemy)
        ├── galpones/
        │   ├── router.py       # GET/POST /api/galpones, GET/PUT/DELETE /api/galpones/{id}
        │   ├── service.py
        │   ├── schemas.py
        │   └── models.py
        ├── aves/               # Lotes, ingresos, mortalidades
        ├── produccion/         # Registros diarios de huevos
        ├── sanidad/            # Vacunaciones, enfermedades, tratamientos
        ├── alimentacion/       # Consumo y costos de alimento
        ├── reportes/           # Generación y consulta de reportes por período
        ├── sync/
        │   ├── router.py       # POST /api/sync (batch LWW)
        │   └── service.py      # Lógica upsert Last Write Wins
        ├── inventario_foto/
        │   ├── router.py       # POST /api/inventario/procesar, GET /api/inventario/conteo
        │   └── service.py      # Inferencia YOLOv8n (modelo cargado una sola vez al arrancar)
        └── health/
            └── router.py       # GET /api/health (health check Beanstalk)
```

> **Regla:** El modelo YOLOv8n vive en `app/models/yolov8n.pt` (~6 MB). Se carga como singleton al importar el módulo, **nunca** en cada petición.

---

## 5. Modelo de datos — convenciones

Todas las entidades heredan de `BaseModel` (abstracta), que aporta:

```python
id         = CHAR(36) UUID v4  # generado offline en el móvil o en el backend
created_at = DateTime UTC
updated_at = DateTime UTC      # usado como discriminador LWW en sync
deleted_at = DateTime nullable # soft delete — nunca borrar filas físicamente
```

**Regla crítica:** Nunca usar `DELETE` SQL real. Todo borrado es soft delete vía `deleted_at`. Los queries de listado deben filtrar `WHERE deleted_at IS NULL`.

---

## 6. Autenticación y seguridad

| Token | Duración | Almacenamiento |
|---|---|---|
| Access Token | 60 minutos | Header `Authorization: Bearer <token>` |
| Refresh Token | 30 días | BD (con hash), enviado en body |

- Algoritmo JWT: **HS256**
- Hash de contraseñas: **bcrypt, 12 rondas** (passlib)
- Todo endpoint protegido usa `Depends(get_current_user)` — sin excepción
- Endpoints públicos: `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/health`

---

## 7. Sincronización offline (módulo `sync/`)

El módulo sync es el más crítico del sistema. Recibe un batch de operaciones desde el móvil y las aplica con estrategia **Last Write Wins (LWW)** usando `updated_at` como discriminador.

```
POST /api/sync
Body: {
  "operations": [
    {
      "table":      "produccion",
      "operation":  "CREATE" | "UPDATE" | "DELETE",
      "record_id":  "<uuid-v4>",
      "payload":    { ...campos },
      "updated_at": "2025-06-01T10:00:00Z"
    }
  ]
}
```

**Lógica LWW:**
1. Para `CREATE`/`UPDATE`: buscar el registro por `record_id`. Si no existe → insertar. Si existe → comparar `updated_at`. Si el `updated_at` del payload es **mayor**, aplicar; si es igual o menor, descartar.
2. Para `DELETE`: aplicar soft delete si el `updated_at` del payload es mayor que el del registro en BD.
3. Responder con un resumen de operaciones aplicadas, omitidas y errores.

**Nunca** lanzar excepción si una operación individual falla; registrar el error en la respuesta y continuar con las demás.

---

## 8. Variables de entorno

| Variable | Ejemplo | Obligatoria |
|---|---|---|
| `DATABASE_URL` | `mysql+aiomysql://admin:***@galpyra-db.xxx.rds.amazonaws.com/galpyra` | Sí |
| `JWT_SECRET` | cadena aleatoria ≥ 64 chars | Sí |
| `JWT_ALGORITHM` | `HS256` | Sí |
| `ENVIRONMENT` | `production` / `development` | Sí |
| `AWS_S3_BUCKET` | `galpyra-media` | Sí |

- En **producción**: configurar en Elastic Beanstalk → Environment Properties. Nunca en código.
- En **desarrollo local**: archivo `.env` en la raíz (está en `.gitignore`).
- `app/core/config.py` las lee con pydantic-settings.

---

## 9. Pool de conexiones (database.py)

```python
pool_size      = 10   # conexiones activas simultáneas
max_overflow   = 20   # extra en picos
pool_pre_ping  = True # verifica antes de usar
pool_recycle   = 3600 # recicla cada hora (evita timeouts MySQL)
```

> RDS db.t3.micro tiene `max_connections ≈ 66`. El pool no debe superar 30 conexiones totales.

---

## 10. Migraciones (Alembic)

```bash
# Crear migración a partir de cambios en los modelos SQLAlchemy
alembic revision --autogenerate -m "descripcion_del_cambio"

# Aplicar todas las migraciones pendientes
alembic upgrade head

# Revertir la última migración
alembic downgrade -1
```

**Regla:** Todo cambio de esquema (nueva tabla, columna, índice) debe tener su migración versionada. Nunca modificar directamente en RDS sin pasar por Alembic.

---

## 11. Testing

| Tipo | Herramienta | Cobertura mínima |
|---|---|---|
| Unitarios | pytest | Servicios, JWT utils, validaciones |
| Integración | pytest + httpx | Endpoints completos (BD SQLite en memoria) |
| Sync / LWW | pytest | CREATE, UPDATE, DELETE, conflictos LWW |

Coberturas objetivo:
- `auth/`: 90%
- `sync/`: 85%
- Módulos de dominio: 75%

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=app --cov-report=term-missing
```

---

## 12. Despliegue (AWS Elastic Beanstalk)

```bash
# Inicializar EB CLI (solo primera vez)
eb init galpyra-backend -r us-east-1 -p python-3.11

# Desplegar rama actual
eb deploy galpyra-prod --staged
```

- **Punto de entrada:** `application.py` → `from app.main import app as application`
- **Health check:** `GET /api/health` cada 30 s; 3 fallos consecutivos = instancia unhealthy
- **CI/CD:** GitHub Actions con OIDC (sin access keys hardcodeadas). Ver `.github/workflows/`

---

## 13. Estado de implementación vs requerimientos (análisis 2026-03-15)

Comparación entre `GALPyra_Requerimientos_Completo.pdf` y el código actual.

| Requerimiento | Estado | Brecha principal |
|---|---|---|
| RF-BACK-001 Arquitectura base | ✅ Completo | — |
| RF-BACK-002 Autenticación JWT | ⚠️ Casi completo | Refresh token implementado en 30 días; PDF especifica 7 días |
| RF-BACK-003 Galpones y Lotes | ⚠️ Parcial | Path lotes-por-galpón difiere; falta validar capacidad al crear lote; falta 409 al borrar galpón con lotes activos |
| RF-BACK-004 Mortalidad | ⚠️ Parcial | Endpoint flat (`POST /mortalidad`), no anidado (`POST /lotes/{id}/mortalidad`); falta historial filtrado por fecha; falta tasa de mortalidad acumulada |
| RF-BACK-005 Producción de Huevos | ⚠️ Parcial | Falta cálculo automático de `porcentaje_postura`; falta validación de fecha única por lote; faltan promedios semanal/mensual |
| RF-BACK-006 Sanidad | ⚠️ Parcial | Enum `TipoEventoSanitario` incorrecto (tiene `ENFERMEDAD`/`REVISION`; debe ser `DIAGNOSTICO`/`INSPECCION`); falta trazabilidad pública con token |
| RF-BACK-007 Alimentación | ⚠️ Parcial | Falta cálculo de conversión alimenticia (`kg_alimento / kg_huevo`) |
| RF-BACK-008 Dashboard | ❌ No implementado | Módulo completo ausente — `GET /api/dashboard` no existe |
| RF-BACK-009 Reportes | ⚠️ Parcial | `generar` crea URL dummy, no genera PDF real; faltan `POST /api/trazabilidad/token` y `GET /api/trazabilidad/{token}` (público, sin JWT) |
| RF-BACK-010 Sync Offline | ⚠️ Parcial | Solo soporta `produccion_huevos` y `movimiento_aves`; faltan: `galpones`, `lotes_aves`, `eventos_sanitarios`, `alimentacion_registros` |

### Pendientes por prioridad

1. **[ALTA]** `GET /api/dashboard` — módulo completo faltante (RF-BACK-008). Debe consolidar: total aves activas, producción últimos 7 días, tasa mortalidad, alertas. Respuesta < 2 seg, caché 5 min.
2. **[ALTA]** Trazabilidad pública — `POST /api/trazabilidad/token` (genera UUID con vigencia) y `GET /api/trazabilidad/{token}` (sin JWT, comparte historial sanitario) (RF-BACK-006/009).
3. **[ALTA]** Completar entidades en sync LWW — agregar soporte para `galpones`, `lotes_aves`, `eventos_sanitarios`, `alimentacion_registros` en `sync/service.py` (RF-BACK-010).
4. **[MEDIA]** Calcular `porcentaje_postura` automáticamente en `produccion/service.py` (RF-BACK-005).
5. **[MEDIA]** Corregir enum `TipoEventoSanitario`: reemplazar `ENFERMEDAD` → `DIAGNOSTICO` y `REVISION` → `INSPECCION` en `app/shared/enums.py` + migración Alembic (RF-BACK-006).
6. **[MEDIA]** Cálculo de conversión alimenticia en `alimentacion/service.py` (RF-BACK-007).
7. **[MEDIA]** Historial de mortalidad con filtros de fecha y tasa acumulada — `GET /api/lotes/{id}/mortalidad` (RF-BACK-004).
8. **[BAJA]** Ajustar duración de refresh token de 30 días a 7 días en `core/security.py` (RF-BACK-002).

### Detalles de implementación actuales (referencia rápida)

- **Lotes por galpón:** `GET /api/lotes/galpon/{galpon_id}` (el PDF pide `GET /api/galpones/{id}/lotes`)
- **Mortalidad:** `POST /api/mortalidad` flat (el PDF pide `POST /api/lotes/{id}/mortalidad`)
- **Sync path:** `POST /api/sync` (el PDF especifica `POST /api/sync/upload`)
- **`app/core/`** tiene archivos adicionales no en CLAUDE.md original: `exceptions.py`, `responses.py`, `seed.py`
- **`app/shared/`** contiene: `base_model.py`, `enums.py`, `paginated.py`, `utils.py`

---

## 14. Reglas que no se negocian

1. **No hay SQL crudo** fuera de los modelos SQLAlchemy. Usar ORM o `text()` solo para queries analíticos muy específicos.
2. **No borrar filas físicamente.** Solo soft delete via `deleted_at`.
3. **No hardcodear credenciales.** Ni en código, ni en commits, ni en comentarios.
4. **No añadir dependencias** sin actualizar `requirements.txt` y documentar el motivo.
5. **No crear endpoints nuevos** sin su test de integración correspondiente.
6. **No usar Hive** ni ninguna otra solución NoSQL. La BD local del móvil es Drift/SQLite; la remota es MySQL.
7. **Scope discipline:** no agregar funcionalidades no definidas en los requisitos del Proyecto Integrador III.

---

## 14. Comandos útiles (desarrollo local)

```bash
# Crear entorno virtual
python -m venv venv
source venv/bin/activate          # Linux/macOS
venv\Scripts\activate             # Windows Git Bash

# Instalar dependencias
pip install -r requirements.txt

# Arrancar servidor de desarrollo
uvicorn app.main:app --reload --port 8000

# Documentación interactiva (mientras corre el servidor)
# http://localhost:8000/docs   → Swagger UI
# http://localhost:8000/redoc  → ReDoc

# Aplicar migraciones locales
alembic upgrade head
```
