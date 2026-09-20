# Pollito Casero

Sistema de gestión de **El Pollito Casero** (San Martín, Mendoza): pedidos mayoristas, pesada con tara, carga de camiones, reparto con GPS, cobros y cuentas corrientes. Reemplaza a la PWA anterior y al ERP GC/Atuq.

Una sola app (Android + escritorio en el navegador) para cuatro roles: `admin`, `preventista`, `cobrador` y, más adelante, `cliente`. La especificación completa está en [docs/PROMPT.md](docs/PROMPT.md); las pantallas de referencia en [docs/diseno](docs/diseno).

## Stack

| Capa | Tecnología |
| --- | --- |
| App | Expo SDK 57 + Expo Router + React Native Web, NativeWind 4, TanStack Query, Zustand |
| API | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2 |
| Base | PostgreSQL 16 · Redis 7 (Docker Compose) |
| Contrato | OpenAPI → `packages/api-client` (openapi-typescript + openapi-fetch) |

```
pollito-casero/
├─ apps/
│  ├─ mobile/        # Expo (Android, Web). Código en src/, rutas en src/app/
│  └─ api/           # FastAPI. app/core · app/domain · app/modules · app/integrations · app/workers
├─ packages/
│  └─ api-client/    # tipos TS generados del OpenAPI (no editar a mano)
└─ docs/             # PROMPT.md (especificación), diseno/ (Stitch), referencia/ (reglas del sistema viejo)
```

## Levantar todo desde cero

Requisitos: **Node 24**, **uv** (instala Python 3.12 solo), **Docker Desktop** (solo para Postgres y Redis).

```bash
# 1. Infraestructura (a partir de la Fase 2; la Fase 0 no la necesita)
docker compose up -d

# 2. API
cd apps/api
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/health  ·  http://localhost:8000/docs

# 3. App (desde la raíz del repo)
npm install
npm run api:openapi          # genera packages/api-client/src/schema.d.ts (requiere apps/api/openapi.json, ver abajo)
npm run mobile:web           # http://localhost:8081
npm run mobile               # QR para Expo Go en Android
```

Para regenerar `apps/api/openapi.json`: `cd apps/api && uv run python scripts/exportar_openapi.py`.

En un celular Android físico la app no llega a `localhost`: copiá `apps/mobile/.env.example` a `.env` y poné la IP de tu PC en `EXPO_PUBLIC_API_URL` (sin `.env`, la app usa la IP que expone Metro).

## Verificación

```bash
# API
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest -q

# App y cliente (desde la raíz)
npm run typecheck && npm run lint && npm test
```

Lo mismo corre en GitHub Actions ([.github/workflows/ci.yml](.github/workflows/ci.yml)): el job de la API exporta el OpenAPI y el job de la app genera el cliente TS a partir de él, así un cambio de contrato rompe la compilación de la app.

## Estado por fase

| Fase | Entregable | Estado |
| --- | --- | --- |
| 0 | Monorepo, Docker Compose, FastAPI `/health`, Expo en web y Android, CI | **Hecha** (ver abajo) |
| 1 | `app/domain/` con tests: precios, tara y neto, aplicación de pagos, saldos, numeración de remitos | Pendiente |
| 2 | Esquema Alembic + módulos `auth`, `sucursales`, `catalogo`, `clientes`. Cliente TS generado | Pendiente |
| 3 | Módulos `pedidos`, `pesada`, `flota`. WebSockets. Semillas | Pendiente |
| 4 | App del repartidor: pantallas de campo, offline con SQLite, cámara, Google Maps, push | Pendiente |
| 5 | Módulo `cobros` + rol cobrador + PDFs y Excel en el worker | Pendiente |
| 6 | Administración en escritorio | Pendiente |

### Fase 0 — qué quedó hecho

- Monorepo con npm workspaces (`apps/mobile`, `packages/api-client`) y proyecto `uv` en `apps/api`.
- `docker-compose.yml` con Postgres 16 y Redis 7 con healthchecks.
- FastAPI con `GET /health`, configuración por `pydantic-settings`, logging con `structlog`, CORS para la app. Test con `httpx`. `ruff`, `mypy --strict` y `pytest` en verde.
- Expo SDK 57 con Expo Router (`src/app/`), NativeWind 4 con los tokens del sistema de diseño en [apps/mobile/tailwind.config.js](apps/mobile/tailwind.config.js) y [apps/mobile/src/theme/tokens.js](apps/mobile/src/theme/tokens.js), fuente Inter, TanStack Query y un store Zustand de sesión. La pantalla inicial consulta `/health` y muestra el estado (color + ícono + texto). `tsc`, `eslint` y `jest` en verde.
- `packages/api-client`: script que exporta el OpenAPI y genera los tipos TS; `crearClienteApi()` con `openapi-fetch` y cabecera `Authorization`.
- CI en GitHub Actions con los dos jobs encadenados.

### Fase 0 — qué falta o quedó a verificar

- **Android**: la app se levanta con `npm run mobile` y Expo Go; no se probó en un dispositivo desde esta máquina (sin emulador). Web sí quedó verificada contra la API en vivo.
- **Docker Compose**: escrito pero no levantado en esta máquina (Docker Desktop apagado). Se valida en la Fase 2, cuando la API empiece a usar Postgres.
- CI no corrió todavía porque el repositorio es local; corre en el primer push.
