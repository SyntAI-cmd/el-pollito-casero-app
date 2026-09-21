# Pollito Casero

Sistema de gestión de **El Pollito Casero** (San Martín, Mendoza): pedidos mayoristas, pesada con tara, carga de camiones, reparto por zonas, cobros y cuentas corrientes. Reemplaza a la PWA anterior y al ERP GC/Atuq.

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
└─ docs/             # PROMPT.md (especificación), diseno/ (pantallas de referencia de Stitch)
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
# Worker de documentos (opcional): con WORKER_MODO=arq en .env, correr aparte
uv run arq app.workers.settings.WorkerSettings
# Sin Redis (por defecto WORKER_MODO=inline) los PDF/Excel se generan en el mismo proceso.
ADMIN_CLAVE=una-clave-larga uv run python -m scripts.semillas   # sucursal, productos, listas, vehículos y usuario admin
# Equipo real (admins, preventistas y cobradores) con una clave inicial que cada uno cambia después
ADMIN_CLAVE=... EQUIPO_CLAVE=clave-inicial uv run python -m scripts.semillas --equipo
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

En un celular Android físico la app no llega a `localhost`: copiá `apps/mobile/.env.example` a `.env` y poné la IP de tu PC en `EXPO_PUBLIC_API_URL` (sin `.env`, la app usa la IP que expone Metro). La API tiene que escuchar en todas las interfaces: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`, y Windows tiene que dejar pasar los puertos 8000 y 8081 en el firewall (red privada).

### Claves externas

| Variable | Dónde | Para qué |
|---|---|---|
| `JWT_SECRET`, `DATABASE_URL`, `REDIS_URL`, `URL_PUBLICA`, `WORKER_MODO=arq` | Railway | Producción (ver "Qué falta"). |

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
| 4 | App del repartidor: pantallas de campo, offline con SQLite, cámara, push | **Hecha** (ver abajo) |
| 5 | Módulo `cobros` + rol cobrador + PDFs y Excel en el worker | **Hecha** (ver abajo) |
| 6 | Administración en escritorio | **Hecha** (ver abajo) |

### Fase 1 — reglas de negocio puras

`apps/api/app/domain/`: `dinero` (Decimal, jamás float), `precios` (listas por turno y zona, precio propio que pisa la lista, totales solo en el servidor), `pesada` (tara por cajón antes de repartir un lote, cajones idempotentes por id), `pagos` (cobro mixto, comprobante obligatorio en transferencia y cheque, aplicación al pedido más viejo), `saldos` (extracto reconstruido desde pedidos y pagos, envases), `cierre_caja`, `pedidos` (estados y cierre del camión), `remitos` (correlativo de 5 dígitos), `telefonos`. Un test vigila que el dominio no importe FastAPI ni SQLAlchemy.

### Fase 2 — esquema y primeros módulos

- Esquema completo (23 tablas) en `apps/api/alembic/versions/`, generado desde los modelos. UUID en todas las claves, `NUMERIC(12,2)` para importes, `NUMERIC(9,3)` para kilos, `TIMESTAMPTZ`, JSONB para campos flexibles, `sucursal_id` en clientes, pedidos, cajones, cobros y cierres. El correlativo de remitos vive en la tabla `contadores` y se toma con `FOR UPDATE` dentro de la transacción del pedido.
- Módulos `auth` (login, refresh con rotación, salir, `/auth/yo`, alta y baja de usuarios), `sucursales` (+ zonas), `catalogo` (productos y listas de precio por lista/turno/zona) y `clientes` (ficha, precios propios, precios resueltos, envases). Cada módulo: `router → service → repository → models`; el filtrado por rol se hace en el service: un preventista solo ve sus clientes y los sin asignar, un cobrador solo sus cuentas.
- Toda operación deja fila en `audit_log` dentro de la misma transacción.
- Tests de integración (`apps/api/tests/`) sobre base real: SQLite en un archivo temporal si no hay Docker, Postgres si `DATABASE_URL_TEST` está definida (así corre CI, que además aplica las migraciones y verifica con `alembic check` que el esquema no se desvió de los modelos).

Migraciones verificadas contra Postgres 16 real (`alembic upgrade head` + `alembic check`) y los 94 tests corren en verde tanto en SQLite como en Postgres (`DATABASE_URL_TEST`). Si Docker Desktop no arranca con "The file cannot be accessed by the system" sobre un `.sock`, renombrar las carpetas `%LOCALAPPDATA%\Docker\run` y `%LOCALAPPDATA%\docker-secrets-engine` y relanzarlo.

### Fase 3 — pedidos, pesada, flota y tiempo real

- **Pedidos**: alta con precios resueltos en el servidor (precio tipeado > propio > lista por turno y zona; sin nada, el renglón queda "sin precio"), número de remito correlativo tomado de `contadores` con `FOR UPDATE`, estados con transiciones validadas, cancelación con motivo, corrección de precios por renglón (con opción de guardarlo como propio), borrado que deja la foto del pedido en `audit_log` y devuelve lo cobrado como saldo a favor, historial en `pedido_eventos`, y `GET /pedidos/dia` (la nota del día: totales por producto y pedidos por preventista).
- **Pesada**: `POST /pedidos/{id}/cajones` (un cajón, id generada en el celular) y `/cajones/lote` (N cajas con bruto total; ids derivadas del `lote_id` con uuid5, así el reintento no duplica). La tara sale de la sucursal (`PATCH /sucursales/{id}` con `tara`). Cada pesada recalcula importes y totales con el precio del cliente; si el pedido ya estaba pagado, la diferencia va al saldo a favor. Anular con motivo, cargar/descargar al camión.
- **Flota**: vehículos, salida del día (`PUT /salidas`: vehículo + hasta dos preventistas, un preventista en un solo vehículo por día), **cerrar camión** (avisa qué falta pesar o cargar por número de remito y pide motivo para salir igual; los pedidos pasan a `en_camino`) y `GET /salidas?fecha=` con las salidas del día.
- **WebSocket** `/ws?token=…`: un canal por sucursal, cada evento con los roles que pueden verlo (`pedido.creado`, `pedido.estado`, `pedido.actualizado`, `pedido.eliminado`, `salida.cerrada`, `flota.posicion`). Difusor en memoria; para varios workers se cambia por Redis pub/sub sin tocar los módulos.
- **Semillas**: `scripts/semillas.py` (base) y `--prueba` / `--borrar-prueba` (datos de prueba, idempotentes).
- 78 tests (dominio + integración), `mypy --strict` y `ruff` en verde.

### Fase 4 — app del repartidor

- **Sesión**: login con JWT, refresh automático y rotación (un solo refresh en vuelo), persistida en `expo-secure-store` (localStorage en web). Un grupo de rutas por rol: `(reparto)`, `(cobrador)`, `(admin)`; `index` redirige según el rol del token.
- **Pantallas de campo** (`apps/mobile/src/app/(reparto)/`): Inicio de reparto (métrica del día, salida, accesos rápidos, entregas prioritarias) · Mis entregas (order cards con stepper, llamar y navegar) · Entrega en curso (cliente y domicilio, total a cobrar, envases devueltos, marcar entregado) · Balanza (elegir pedido → producto → bruto; neto en grande; por cajón o por lote; anular con motivo) · Carga del camión (armar salida, marcar cajones, cerrar camión con motivo si hay faltantes) · Cargar pedido (búsqueda de cliente, cajas o kilos, precio editable en la fila con opción de guardarlo como propio).
- **Offline**: `expo-sqlite` como copia local de lo que la pantalla muestra (`lib/almacen.ts`; localStorage en web) y **cola de mutaciones** (`lib/cola.ts`) con id generada en el celular, reintento en orden que se frena en el primer fallo de red, y rechazos del servidor que no se reintentan sino que se muestran con su mensaje. La pesada se escribe local y se ve al instante (`lib/pesadaLocal.ts`); indicador visible de operaciones pendientes en todas las pantallas.
- **Tiempo real**: WebSocket a `/ws` con reconexión; los eventos invalidan las consultas.
- **Push**: `expo-notifications` registra el token en `POST /auth/push-token`; el servidor avisa al preventista cuando administración le asigna un pedido (`integrations/push.py`, Expo Push).
- **Cámara**: `lib/foto.ts` saca la foto y la reduce a ≤ 3,5 MB (se usa en el cobro, Fase 5).
- Sistema de diseño en componentes: `Boton`, `Tarjeta`/`MetricaHero`/`GrillaAccesos`, `Badge`/`Stepper`, `TarjetaPedido`, `Campo`, `NavFlotante` con FAB. Nunca un estado solo con color; área táctil mínima 48 px; numerales tabulares.
- Verificado en el navegador contra la API con datos de prueba: login, inicio, balanza (el cajón llegó al servidor con bruto 21,7 → neto 20 y el total se recalculó).

**Pendiente / a verificar**: el cobro con foto se construye en la Fase 5 junto con su API.

### Fase 5 — cobros, cobrador y documentos

- **Cobros** (`app/modules/cobros`): `POST /pagos` con partes mixtas (efectivo, transferencia, cheque) que deben sumar el total; transferencia y cheque exigen `comprobante_id` de una foto subida con `POST /comprobantes` (multipart, ≤ 4 MB, guardada en storage con URL firmada servida por `/archivos/...`). Con `pedido_id` es el cobro en la entrega (descuenta el saldo a favor del cliente y marca el pedido pagado); sin `pedido_id` es un pago a cuenta que cubre pedidos enteros del más viejo al más nuevo y deja el sobrante a favor. `idempotencia` generada en el celular: el reintento devuelve el mismo pago.
- **Cuenta corriente**: `GET /clientes/{id}/extracto` se reconstruye desde pedidos a cuenta (cargo por el estimado original, ajuste al pesar, anulación), pagos y `ajustes_cuenta` (reintegro por pedido borrado, repesada de un pedido pagado, uso de saldo a favor, ajuste manual de administración). Saldo negativo = saldo a favor.
- **Entrega**: `POST /pedidos/{id}/estado` a `entregado` exige al menos una foto (comprobante o remito firmado).
- **Cobrador**: `GET /cobranzas/cuentas` (sus clientes con saldo, por zona), `GET /caja?fecha=` (efectivo esperado, transferencias y cheques aparte, cobros del día) y `POST /caja/cierres` (diferencia y nota obligatoria si no cuadra; administración puede cerrar la caja de otro). En la app: pestañas **Cuentas** y **Caja**, y la pantalla de cobro compartida con el preventista (`components/Cobro.tsx`: partes, cámara con reducción a ≤ 3,5 MB, subida del comprobante; un cobro solo en efectivo va por la cola offline).
- **Documentos** (`app/modules/documentos` + `app/workers`): `POST /documentos` encola y `GET /documentos/{id}` devuelve la URL firmada cuando está listo. Tipos: `remitos` (réplica del talonario impreso de 10 × 15: logo, cuadro X, datos fiscales, N° y fecha, cliente/calle/localidad/cel., 12 renglones KILOS · DETALLE · PRECIO X UNIDAD · PRECIO TOTAL, CAJAS ADEUDADAS con saldo de cuenta corriente y TOTAL; `formato: "a4"` imprime 4 por hoja con marcas de corte y `"10x15"` uno por página para el talonario), `hoja_pedidos` (A4 apaisada por turno y preventista), `hoja_ruta` (26 pedidos por hoja con columnas en blanco y cuadro de rendición), `tickets` (comandera 80 mm, un casillero por caja) y `consolidado` (Excel, una fila por pedido con fórmulas de totales). ReportLab + openpyxl; worker `arq` sobre Redis o modo `inline` sin Redis.
- 91 tests en la API; verificado en el navegador: cuentas a cobrar y cobro a cuenta del cobrador con datos de prueba (`--prueba` ahora crea también `prueba.cobra`).

### Fase 6 — administración en escritorio

- Grupo `(admin)` con barra lateral oscura en ≥ 1024 px (tira horizontal en pantallas chicas), contenido a 1280 px máximo. Pantallas: **Nota del día** (noticias del equipo, totales por producto, pedidos por preventista, accesos a pesar/cargar/imprimir), **Pedidos** (lista densa con columnas fijas o tarjetas, filtros por fecha/turno/estado/preventista, y **vista partida 7/5** con la ficha del pedido: renglones con precio editable, comprobantes, cambio de estado, cancelación con motivo, borrado), **Cargar pedido** (formulario compartido con el repartidor + preventista y segundo preventista), **Clientes** (lista, alta, ficha editable, precios propios, envases, ajuste manual y extracto), **Listas de precios** (producto × lista por turno y zona; Ctrl+Enter guarda), **Balanza** y **Carga** (las pantallas de piso), **Salidas** (armar salida, faltantes, cerrar camión), **Rendición** (una caja por persona con cierre y comprobantes del día), **Imprimir** (genera y descarga/comparte/imprime los documentos), **Equipo** (usuarios y vehículos), **Sucursales** (tara y zonas).
- API: módulo `comunicacion` (`/noticias`, `/mensajes`, con eventos por WebSocket) y `GET /caja/rendicion`.
- Verificado en el navegador como admin con datos de prueba: nota del día y vista partida de pedidos. 94 tests en la API; `tsc`, `eslint` y `jest` en verde en la app.

### Después de la Fase 6 — hecho

- Logo real en la app (ícono, splash, login) y en el remito; remito igual al talonario, en A4 (4 por hoja) o 10 × 15.
- **Sin mapas ni GPS (decisión de MVP, 21/09/2026)**: se sacaron geocoding, coordenadas de clientes, `react-native-maps`, `expo-location` y la posición de los camiones (migración `dc13e1927526`). El reparto se organiza por **zona y domicilio**; «Cómo llegar» del cobrador abre la app de mapas del celular con la dirección escrita. Si algún día hace falta, está en la historia de git (commit "Logo y remito del talonario, geocoding con Google…").
- Semillas `--equipo` con el equipo real; catálogo con "Suprema de muslo" y "Otro producto" (sin lista: precio propio por pedido).
- Postgres real validado con Docker; `docs/referencia` (datos del sistema viejo con teléfonos y CUITs) fuera del repo y de su historia.

### Qué falta

- Hacer el build con EAS (`eas build -p android`).
- Deploy: Railway con Postgres + Redis + worker (`arq`) y `WORKER_MODO=arq`; storage S3-compatible en lugar del disco local (`integrations/storage.py`).
- Rol `cliente` (catálogo, sus pedidos, seguimiento, cuenta corriente y envases).
- Chat interno en la app (la API ya lo tiene).

### Fase 0 — qué quedó hecho

- Monorepo con npm workspaces (`apps/mobile`, `packages/api-client`) y proyecto `uv` en `apps/api`.
- `docker-compose.yml` con Postgres 16 y Redis 7 con healthchecks.
- FastAPI con `GET /health`, configuración por `pydantic-settings`, logging con `structlog`, CORS para la app. Test con `httpx`. `ruff`, `mypy --strict` y `pytest` en verde.
- Expo SDK 57 con Expo Router (`src/app/`), NativeWind 4 con los tokens del sistema de diseño en [apps/mobile/tailwind.config.js](apps/mobile/tailwind.config.js) y [apps/mobile/src/theme/tokens.js](apps/mobile/src/theme/tokens.js), fuente Inter, TanStack Query y un store Zustand de sesión. La pantalla inicial consulta `/health` y muestra el estado (color + ícono + texto). `tsc`, `eslint` y `jest` en verde.
- `packages/api-client`: script que exporta el OpenAPI y genera los tipos TS; `crearClienteApi()` con `openapi-fetch` y cabecera `Authorization`.
- CI en GitHub Actions con los dos jobs encadenados.

### Fase 0 — qué falta o quedó a verificar

- **Android**: la app se levanta con `npm run mobile` y Expo Go; no se probó en un dispositivo desde esta máquina (sin emulador). Web sí quedó verificada contra la API en vivo.
- **Docker Compose**: quedó validado en la Fase 2+ (ver arriba).
