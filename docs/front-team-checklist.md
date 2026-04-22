# Checklist para equipo Frontend

## Estado actual del backend

El backend de GALPyra ya quedó en un estado estable para integrar con Flutter y para preparar staging en AWS.

### Estado general
- 24 pruebas automatizadas pasando
- Auth, sync, dashboard, trazabilidad, inventario, reportes, producción, sanidad, alimentación, galpones y aves funcionales
- Seguridad endurecida con JWT, refresh token hash, headers de seguridad y rate limiting básico
- OpenAPI documentado en los routers de dominio
- Contratos ajustados para la integración con Flutter

### Lo que ya está alineado
- Login devuelve access_token, refresh_token, token_type y user
- Sync acepta operaciones offline y responde con procesadas, fallidas y detalles
- Dashboard devuelve las 4 métricas requeridas
- Inventario procesa imagen con campo imagen o file
- Reportes expone url_reporte para descarga
- Trazabilidad pública funciona sin JWT para consultar un token válido

### Lo que sigue pendiente fuera del backend
- Integración real con Flutter
- Validación en staging o producción AWS
- Smoke test completo desde la app móvil

## Contratos principales para Flutter

### Autenticación
- POST /api/auth/login
  - Entrada: email, password
  - Salida: access_token, refresh_token, token_type, user
- POST /api/auth/refresh
  - Entrada: refresh_token
  - Salida: access_token, refresh_token, token_type
- POST /api/auth/logout
  - Entrada: refresh_token
  - Salida: mensaje de cierre
- GET /api/auth/me
  - Requiere JWT válido

### Dashboard
- GET /api/dashboard
  - Requiere JWT válido
  - Salida: total_aves_activas, produccion_ultimos_7_dias, tasa_mortalidad_porcentaje, alertas

### Sync offline
- POST /api/sync
  - Requiere JWT válido
  - Entrada: operaciones con id, operacion, entidad, payload, created_at
  - Salida: procesadas, fallidas, detalles
- GET /api/sync/logs
  - Requiere JWT válido

### Inventario por foto
- POST /api/inventario/procesar
  - Requiere JWT válido
  - Usa multipart/form-data
  - Campo de archivo aceptado: imagen o file
  - Campos opcionales: lote_id, galpon_id
- POST /api/inventario/confirmar
  - Requiere JWT válido
- GET /api/inventario/jobs
  - Requiere JWT válido
- GET /api/inventario/jobs/{job_id}
  - Requiere JWT válido

### Reportes
- POST /api/reportes/generar
  - Requiere JWT válido
  - Entrada: tipo, fecha_inicio, fecha_fin, formato
  - Salida: url_reporte
- GET /api/reportes
  - Requiere JWT válido
- GET /api/reportes/{reporte_id}
  - Requiere JWT válido

### Trazabilidad pública
- POST /api/trazabilidad/token
  - Requiere JWT válido
- GET /api/trazabilidad/{token}
  - No requiere JWT

### Módulos de dominio
- Galpones: /api/galpones
- Lotes: /api/lotes y /api/lotes/galpon/{galpon_id}
- Producción: /api/produccion, /api/produccion/rango, /api/produccion/galpon/{galpon_id}
- Sanidad: /api/sanidad y /api/sanidad/historial/{lote_id}
- Alimentación: /api/alimentacion y /api/alimentacion/conversion/{lote_id}

## Checklist de integración Flutter

### Autenticación y sesión
- [ ] Guardar access_token después del login
- [ ] Guardar refresh_token de forma segura
- [ ] Enviar Authorization: Bearer <token> en rutas protegidas
- [ ] Renovar sesión usando /api/auth/refresh antes de expirar el access token
- [ ] Manejar logout invalidando el refresh token
- [ ] Mostrar estado de sesión expirada si el backend responde 401

### Formato estándar de respuestas
- [ ] Leer siempre el objeto success
- [ ] Mostrar el message como texto principal de feedback
- [ ] Tomar los datos desde data
- [ ] Usar status_code para decisiones de UI cuando aplique
- [ ] Manejar error como estructura secundaria en respuestas fallidas

### Manejo de errores
- [ ] 401: redirigir al login o renovar sesión
- [ ] 422: mostrar errores de validación de formulario
- [ ] 429: mostrar mensaje de espera y reintento
- [ ] 500: mostrar error genérico y registrar incidente

### Inventario por foto
- [ ] Enviar la imagen con el campo imagen preferiblemente
- [ ] Mantener compatibilidad con file si ya existe en la app
- [ ] Enviar lote_id o galpon_id según el flujo de pantalla
- [ ] Confirmar conteo con el job_id retornado
- [ ] Consultar jobs para historial de procesamiento

### Sync offline
- [ ] Construir cola local de operaciones
- [ ] Incluir id estable por operación
- [ ] Enviar operacion, entidad, payload y created_at en formato ISO 8601
- [ ] Soportar operaciones CREATE, UPDATE, DELETE y UPSERT
- [ ] Reintentar fallas parciales sin bloquear toda la cola
- [ ] Leer detalles de respuesta para saber qué fue procesado o descartado

### Reportes
- [ ] Consumir url_reporte como enlace descargable
- [ ] Tratar el reporte como recurso generado por el backend
- [ ] Mostrar estado de generación si la respuesta tarda

### Dashboard
- [ ] Refrescar las métricas al abrir la pantalla
- [ ] Usar total_aves_activas, produccion_ultimos_7_dias, tasa_mortalidad_porcentaje y alertas
- [ ] Mostrar alertas como lista simple

### Trazabilidad pública
- [ ] Abrir la consulta del token sin token JWT
- [ ] Mostrar lote y eventos sanitarios devueltos por el backend
- [ ] Manejar token expirado como 410

## Reglas técnicas que el front debe respetar

- [ ] No asumir campos adicionales no documentados
- [ ] No renombrar campos que ya tienen contrato fijo en backend
- [ ] Enviar fechas en ISO 8601 con zona horaria cuando sea posible
- [ ] No depender de respuestas distintas a las ya descritas
- [ ] Tomar el backend como fuente de verdad para estados y validaciones

## Resumen rápido para el equipo

- El backend ya está listo para integrarse
- Los contratos más importantes ya están estables
- El mayor riesgo ahora es desacople de nombres de campos o manejo de tokens en Flutter
- Antes de ir a producción, validar localmente y luego en staging AWS
