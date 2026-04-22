# Checklist de cierre: Flutter + AWS

Estado del backend al momento de este checklist:
- 24 tests pasando
- Auth / sync / dashboard / trazabilidad / inventario / reportes validados
- Seguridad base endurecida
- OpenAPI documentado en routers principales

## 1. Preintegracion con Flutter

### Contratos que deben coincidir
- [ ] `POST /api/auth/login` retorna `access_token`, `refresh_token`, `token_type`, `user`
- [ ] `POST /api/auth/refresh` retorna `access_token`, `refresh_token`, `token_type`
- [ ] `POST /api/auth/logout` invalida refresh token
- [ ] `GET /api/dashboard` retorna `total_aves_activas`, `produccion_ultimos_7_dias`, `tasa_mortalidad_porcentaje`, `alertas`
- [ ] `POST /api/sync` acepta `operaciones` con `id`, `operacion`, `entidad`, `payload`, `created_at`
- [ ] `GET /api/sync/logs` retorna logs compatibles con la app
- [ ] `POST /api/inventario/procesar` acepta `imagen` o `file` con `multipart/form-data`
- [ ] `POST /api/reportes/generar` expone `url_reporte`
- [ ] `GET /api/trazabilidad/{token}` funciona sin JWT

### Verificaciones funcionales
- [ ] Probar login desde Flutter con usuario real de seed
- [ ] Confirmar refresh automático de token en la app
- [ ] Validar que el formulario de inventario envía `imagen` y `galpon_id` o `lote_id`
- [ ] Probar lectura de dashboard con token válido
- [ ] Probar sincronización offline con un lote de operaciones mixtas
- [ ] Probar descarga de reporte desde `url_reporte`
- [ ] Probar consulta pública de trazabilidad desde navegador sin autenticación

### Criterios de aceptación
- [ ] Ningún endpoint crítico devuelve 404 por contrato distinto
- [ ] Ningún endpoint devuelve formato de respuesta distinto a `{ success, message, data, status_code }`
- [ ] Flutter no necesita adaptar nombres de campos salvo casos documentados
- [ ] Los errores 401, 422 y 500 se muestran de forma consistente en la app

## 2. Predeploy a AWS

### Entorno y configuración
- [ ] Definir `DATABASE_URL` real en Elastic Beanstalk
- [ ] Definir `JWT_SECRET` fuerte en Elastic Beanstalk
- [ ] Definir `CORS_ALLOWED_ORIGINS` con dominios reales del frontend
- [ ] Definir `AWS_S3_BUCKET` si se usará subida real de reportes
- [ ] Definir credenciales AWS solo vía Environment Properties o IAM Role

### Elastic Beanstalk
- [ ] `application.py` sigue como entrypoint correcto
- [ ] `.ebextensions/python.config` ejecuta `alembic upgrade head`
- [ ] La app arranca con `application:application`
- [ ] Health check responde `200` en `/api/health`
- [ ] Logs de arranque sin errores de import, migración o settings

### Docker / runtime
- [ ] `Dockerfile` construye imagen sin usar root en runtime
- [ ] `requirements.txt` está totalmente fijado con versiones exactas
- [ ] `.dockerignore` excluye `.env`, `.venv`, cache y artefactos temporales
- [ ] `reportlab` y dependencias críticas instalan correctamente

### Base de datos
- [ ] Migraciones aplicadas en staging
- [ ] Tablas y enums coinciden con el estado de los modelos actuales
- [ ] Soft delete validado en lectura/listado
- [ ] Usuarios seed o datos iniciales no se duplican en cada deploy

### Seguridad mínima de producción
- [ ] CORS no usa wildcard en producción
- [ ] Headers de seguridad presentes
- [ ] Rate limiting habilitado o documentado como pendiente aceptada
- [ ] Secretos nunca quedan en `.env.example` con valores reales

### Smoke test postdeploy
- [ ] `GET /api/health`
- [ ] `POST /api/auth/login`
- [ ] `GET /api/dashboard`
- [ ] `POST /api/sync`
- [ ] `POST /api/inventario/procesar`
- [ ] `POST /api/reportes/generar`
- [ ] `GET /api/trazabilidad/{token}`

## 3. Orden recomendado para salir hoy

1. Congelar contrato Flutter
2. Probar frontend contra backend local
3. Subir a staging en AWS
4. Validar migraciones y health check
5. Ejecutar smoke test completo
6. Solo después pasar a producción

## 4. Notas

- El backend ya quedó funcionalmente estable en el estado actual.
- El siguiente riesgo real ya no es el código base, sino la integración exacta con Flutter y el despliegue con variables reales.
- Si aparece un fallo en predeploy, revisar primero `CORS_ALLOWED_ORIGINS`, `DATABASE_URL`, `JWT_SECRET` y migraciones.
