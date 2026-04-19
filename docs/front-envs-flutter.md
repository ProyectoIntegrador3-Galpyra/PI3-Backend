# Frontend Flutter - Variables por Ambiente

Esta guia deja un flujo reproducible para que el equipo frontend cambie de ambiente sin tocar codigo.

## Variable unica

Usar una sola variable en Flutter:

- `API_BASE_URL`

Ejemplo de uso en codigo:

```dart
const apiBaseUrl = String.fromEnvironment('API_BASE_URL');
```

## Ambientes recomendados

Define estas URLs segun el ambiente:

- Local web: `http://localhost:8000/api`
- Local Android emulator: `http://10.0.2.2:8000/api`
- Staging: `https://<staging-backend-domain>/api`
- Produccion: `https://<production-backend-domain>/api`

## Comandos reproducibles

### 1) Flutter web contra backend local

```bash
flutter run -d chrome --web-port 3000 --dart-define=API_BASE_URL=http://localhost:8000/api
```

### 2) Flutter Android emulator contra backend local

```bash
flutter run -d emulator-5554 --dart-define=API_BASE_URL=http://10.0.2.2:8000/api
```

### 3) Flutter web contra staging

```bash
flutter run -d chrome --web-port 3000 --dart-define=API_BASE_URL=https://<staging-backend-domain>/api
```

### 4) Build web para produccion

```bash
flutter build web --release --dart-define=API_BASE_URL=https://<production-backend-domain>/api
```

## Smoke test rapido

Con la app levantada, validar este flujo:

1. Login (`POST /auth/login`).
2. Perfil (`GET /auth/me`).
3. Refresh (`POST /auth/refresh`).
4. Logout (`POST /auth/logout`).
5. Health (`GET /health`).

Si todo responde 200 y el refresh renueva access token, el ambiente queda operativo.
