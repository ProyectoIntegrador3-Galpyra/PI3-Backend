# PI3-Back - GALPyra Backend

Backend para GALPyra con FastAPI, SQLAlchemy 2.0 async, MySQL 8, Alembic y Pydantic v2.

## Requisitos

- Python 3.11+
- MySQL 8.0

## Estructura principal

```text
PI3-Back/
├── application.py
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── alembic/
├── app/
└── tests/
```

## Configuracion

1. Copia variables de entorno:

```bash
cp .env.example .env
```

2. Crea entorno virtual e instala dependencias:

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Ejecutar con Docker

```bash
docker compose up -d --build
```

API disponible en `http://localhost:8000`.

## Ejecucion local

1. Levanta MySQL (local o con docker).
2. Aplica migraciones.
3. Ejecuta seed.
4. Inicia FastAPI.

```bash
alembic upgrade head
python -m app.core.seed
uvicorn app.main:app --reload --port 8000
```

## Migraciones Alembic

Crear migracion:

```bash
alembic revision --autogenerate -m "descripcion_cambio"
```

Aplicar migraciones:

```bash
alembic upgrade head
```

Revertir una migracion:

```bash
alembic downgrade -1
```

Revertir a version especifica:

```bash
alembic downgrade <revision_id>
```

## Usuario admin seed

- email: `admin@galpyra.com`
- password: `Admin123*`
- nombre: `Administrador GALPyra`
- rol: `ADMIN`

## Modo desarrollo abierto

Los endpoints estan abiertos para facilitar integracion con Flutter y Postman.

- El flujo JWT (login/refresh/logout) ya esta implementado.
- `get_current_user` ya existe en `app/core/dependencies.py`.
- Para endurecer seguridad luego, agrega `Depends(get_current_user)` en los routers que correspondan.

## Pruebas

```bash
pytest -q
```

## Documentacion OpenAPI

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Checklist de cierre

- Guia operativa para integracion con Flutter y despliegue en AWS: [docs/checklist-preintegracion-despliegue.md](docs/checklist-preintegracion-despliegue.md)
- Guia rapida de variables por ambiente para Flutter: [docs/front-envs-flutter.md](docs/front-envs-flutter.md)
