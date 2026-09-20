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
uv run alembic upgrade head                 # crea el esquema en Postgres
ADMIN_CLAVE=una-clave-larga uv run python -m scripts.semillas   # sucursal, productos, listas, vehículos y usuario admin
# Opcional: datos de prueba (2 preventistas, 10 clientes "Prueba N", 10 pedidos para hoy)
ADMIN_CLAVE=... EQUIPO_CLAVE=otra-clave uv run python -m scripts.semillas --prueba   # --borrar-prueba los saca
uv run uvicorn app.main:app --reload --port 8000
# → http://localhost:8000/health  ·  http://localhost:8000/docs

# 3. App (desde la raíz del repo)
npm install
npm run api:openapi          # genera packages/api-client/src/schema.d.ts (requiere apps/api/openapi.json, ver abajo)
npm run mobile:web           # http://localhost:8081
npm run mobile               # QR para Expo Go en Android
```

Para regenerar `apps/api/openapi.json`: `cd apps/api && uv run python -m scripts.exportar_openapi`.

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
| 1 | `app/domain/` con tests: precios, tara y neto, aplicación de pagos, saldos, numeración de remitos | **Hecha** |
| 2 | Esquema Alembic + módulos `auth`, `sucursales`, `catalogo`, `clientes`. Cliente TS generado | **Hecha** (ver abajo) |
| 3 | Módulos `pedidos`, `pesada`, `flota`. WebSockets. Semillas | **Hecha** (ver abajo) |
| 4 | App del repartidor: pantallas de campo, offline con SQLite, cámara, Google Maps, push | **Hecha** (ver abajo) |
| 5 | Módulo `cobros` + rol cobrador + PDFs y Excel en el worker | Pendiente |
| 6 | Administración en escritorio | Pendiente |

### Fase 1 — reglas de negocio puras

`apps/api/app/domain/`: `dinero` (Decimal, jamás float), `precios` (listas por turno y zona, precio propio que pisa la lista, totales solo en el servidor), `pesada` (tara por cajón antes de repartir un lote, cajones idempotentes por id), `pagos` (cobro mixto, comprobante obligatorio en transferencia y cheque, aplicación al pedido más viejo), `saldos` (extracto reconstruido desde pedidos y pagos, envases), `cierre_caja`, `pedidos` (estados y cierre del camión), `remitos` (correlativo de 5 dígitos), `telefonos`. Un test vigila que el dominio no importe FastAPI ni SQLAlchemy.

### Fase 2 — esquema y primeros módulos

- Esquema completo (23 tablas) en `apps/api/alembic/versions/`, generado desde los modelos. UUID en todas las claves, `NUMERIC(12,2)` para importes, `NUMERIC(9,3)` para kilos, `TIMESTAMPTZ`, JSONB para campos flexibles, `sucursal_id` en clientes, pedidos, cajones, cobros y cierres. El correlativo de remitos vive en la tabla `contadores` y se toma con `FOR UPDATE` dentro de la transacción del pedido.
- Módulos `auth` (login, refresh con rotación, salir, `/auth/yo`, alta y baja de usuarios), `sucursales` (+ zonas), `catalogo` (productos y listas de precio por lista/turno/zona) y `clientes` (ficha, precios propios, precios resueltos, envases). Cada módulo: `router → service → repository → models`; el filtrado por rol se hace en el service: un preventista solo ve sus clientes y los sin asignar, un cobrador solo sus cuentas.
- Toda operación deja fila en `audit_log` dentro de la misma transacción.
- Geocoding detrás de `app/integrations/maps.py` (proveedor nulo hasta la Fase 4).
- Tests de integración (`apps/api/tests/`) sobre base real: SQLite en un archivo temporal si no hay Docker, Postgres si `DATABASE_URL_TEST` está definida (así corre CI, que además aplica las migraciones y verifica con `alembic check` que el esquema no se desvió de los modelos).

**Pendiente de verificar en esta máquina**: las migraciones contra Postgres real (Docker Desktop no levantó: error conocido del socket `dockerInference`; se limpió y relanzó, queda validar en CI o cuando el engine arranque).

### Fase 3 — pedidos, pesada, flota y tiempo real

- **Pedidos**: alta con precios resueltos en el servidor (precio tipeado > propio > lista por turno y zona; sin nada, el renglón queda "sin precio"), número de remito correlativo tomado de `contadores` con `FOR UPDATE`, estados con transiciones validadas, cancelación con motivo, corrección de precios por renglón (con opción de guardarlo como propio), borrado que deja la foto del pedido en `audit_log` y devuelve lo cobrado como saldo a favor, historial en `pedido_eventos`, y `GET /pedidos/dia` (la nota del día: totales por producto y pedidos por preventista).
- **Pesada**: `POST /pedidos/{id}/cajones` (un cajón, id generada en el celular) y `/cajones/lote` (N cajas con bruto total; ids derivadas del `lote_id` con uuid5, así el reintento no duplica). La tara sale de la sucursal (`PATCH /sucursales/{id}` con `tara`). Cada pesada recalcula importes y totales con el precio del cliente; si el pedido ya estaba pagado, la diferencia va al saldo a favor. Anular con motivo, cargar/descargar al camión.
- **Flota**: vehículos, salida del día (`PUT /salidas`: vehículo + hasta dos preventistas, un preventista en un solo vehículo por día), **cerrar camión** (avisa qué falta pesar o cargar por número de remito y pide motivo para salir igual; los pedidos pasan a `en_camino`), GPS (`POST /salidas/{id}/ubicacion`, solo el repartidor de esa salida), recorrido (últimos 600 puntos) y `GET /salidas?fecha=` como "flota en vivo" con última posición.
- **WebSocket** `/ws?token=…`: un canal por sucursal, cada evento con los roles que pueden verlo (`pedido.creado`, `pedido.estado`, `pedido.actualizado`, `pedido.eliminado`, `salida.cerrada`, `flota.posicion`). Difusor en memoria; para varios workers se cambia por Redis pub/sub sin tocar los módulos.
- **Semillas**: `scripts/semillas.py` (base) y `--prueba` / `--borrar-prueba` (datos de prueba, idempotentes).
- 78 tests (dominio + integración), `mypy --strict` y `ruff` en verde.

### Fase 4 — app del repartidor

- **Sesión**: login con JWT, refresh automático y rotación (un solo refresh en vuelo), persistida en `expo-secure-store` (localStorage en web). Un grupo de rutas por rol: `(reparto)`, `(cobrador)`, `(admin)`; `index` redirige según el rol del token.
- **Pantallas de campo** (`apps/mobile/src/app/(reparto)/`): Inicio de reparto (métrica del día, salida y GPS, accesos rápidos, entregas prioritarias) · Mis entregas (order cards con stepper, llamar y navegar) · Entrega en curso (mapa, cliente, total a cobrar, envases devueltos, marcar entregado) · Balanza (elegir pedido → producto → bruto; neto en grande; por cajón o por lote; anular con motivo) · Carga del camión (armar salida, marcar cajones, cerrar camión con motivo si hay faltantes) · Cargar pedido (búsqueda de cliente, cajas o kilos, precio editable en la fila con opción de guardarlo como propio).
- **Offline**: `expo-sqlite` como copia local de lo que la pantalla muestra (`lib/almacen.ts`; localStorage en web) y **cola de mutaciones** (`lib/cola.ts`) con id generada en el celular, reintento en orden que se frena en el primer fallo de red, y rechazos del servidor que no se reintentan sino que se muestran con su mensaje. La pesada se escribe local y se ve al instante (`lib/pesadaLocal.ts`); indicador visible de operaciones pendientes en todas las pantallas.
- **Tiempo real**: WebSocket a `/ws` con reconexión; los eventos invalidan las consultas.
- **GPS**: `expo-location` cada 15 s o 25 m mientras la salida está activa (primer plano). **Mapa**: `react-native-maps` con Google en Android; en web un embed de Google Maps con enlace.
- **Push**: `expo-notifications` registra el token en `POST /auth/push-token`; el servidor avisa al preventista cuando administración le asigna un pedido (`integrations/push.py`, Expo Push).
- **Cámara**: `lib/foto.ts` saca la foto y la reduce a ≤ 3,5 MB (se usa en el cobro, Fase 5).
- Sistema de diseño en componentes: `Boton`, `Tarjeta`/`MetricaHero`/`GrillaAccesos`, `Badge`/`Stepper`, `TarjetaPedido`, `Campo`, `NavFlotante` con FAB. Nunca un estado solo con color; área táctil mínima 48 px; numerales tabulares.
- Verificado en el navegador contra la API con datos de prueba: login, inicio, balanza (el cajón llegó al servidor con bruto 21,7 → neto 20 y el total se recalculó).

**Pendiente / a verificar**: en Android físico (Expo Go) no se probó desde esta máquina; la key de Google Maps para builds de producción va en `app.json → android.config.googleMaps.apiKey` (Expo Go usa la suya); GPS en segundo plano requiere build de desarrollo con permiso de background. El cobro con foto se construye en la Fase 5 junto con su API.

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
