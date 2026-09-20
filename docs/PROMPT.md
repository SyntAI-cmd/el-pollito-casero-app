# Prompt para construir "Pollito Casero" (React Native + FastAPI)

> Pegá todo lo que sigue como primer mensaje en un repo vacío, con Claude Code, Codex o el agente que uses.
> Si el agente pregunta, que arranque por la Fase 0 y no avance de fase sin mostrarte lo hecho.

---

## Contexto

Sos el desarrollador de **Pollito Casero**, el sistema de gestión de una empresa avícola de San Martín, Mendoza (Argentina): granja propia, planta de faena y varias sucursales, con reparto mayorista diario a comercios.

Existe un sistema anterior en producción (PWA con React 19 + Vite y un servidor Node sin framework sobre SQLite, repo `SyntAI-cmd/el_pollito_casero_pwa`). **No lo vamos a migrar archivo por archivo**: vamos a construir el sistema nuevo desde cero en este repo, con la arquitectura que se describe abajo, reutilizando únicamente las reglas de negocio ya validadas, que están descritas en este prompt.

El sistema nuevo reemplaza también al ERP externo GC/Atuq que la empresa usa hoy para pedidos, remitos y cuentas corrientes.

## Stack obligatorio

| Capa | Tecnología |
| --- | --- |
| App | React Native con **Expo** (SDK managed) + **Expo Router** + **React Native Web** |
| Estilos | **NativeWind** (Tailwind para RN) con los tokens de diseño de este prompt |
| Datos remotos | **TanStack Query** sobre un cliente TypeScript **generado desde el OpenAPI** |
| Estado local | **Zustand** |
| Offline | **expo-sqlite** como fuente de verdad de la pantalla + cola de mutaciones idempotente |
| Backend | **Python 3.12 + FastAPI** (async), **SQLAlchemy 2.0**, **Alembic**, **Pydantic v2** |
| Base | **PostgreSQL 16** |
| Tareas | **arq** o **Celery** sobre Redis (PDFs, Excel, push) |
| Auth | JWT de acceso corto + refresh token, roles en el token |
| Hosting | Railway (API, Postgres, Redis, worker); builds de la app con EAS |
| CI | GitHub Actions: `ruff` + `mypy` + `pytest` / `tsc` + `eslint` + `jest` |

Nada de Express, nada de ORMs alternativos, nada de Redux. **No incluir Mercado Pago ni ninguna pasarela de pago**: el cobro es presencial (ver "Cobros").

## Estructura del monorepo

```
pollito-casero/
├─ apps/
│  ├─ mobile/                 # Expo (Android, iOS, Web)
│  └─ api/
│     └─ app/
│        ├─ core/             # config, seguridad, dependencias, errores, logging
│        ├─ domain/           # reglas puras, Python sin FastAPI, 100% testeadas
│        ├─ modules/          # un paquete por dominio
│        ├─ integrations/     # maps, push, storage, whatsapp
│        └─ workers/          # tareas en segundo plano
└─ packages/
   └─ api-client/             # cliente TS generado del OpenAPI (no editar a mano)
```

### Reglas de arquitectura, no negociables

1. **Un módulo por dominio, no por capa.** `app/modules/pedidos/` contiene `router.py`, `schemas.py`, `service.py`, `repository.py`, `models.py` y `tests/`. Prohibido crear carpetas globales `controllers/`, `services/` o `models/`.
2. **Cuatro capas, siempre en ese orden**: `router` (HTTP, permisos, validación) → `service` (reglas, transacciones) → `repository` (consultas) → `models` (tablas). **El router nunca toca la base de datos.**
3. **Un módulo llama a otro solo a través de su `service`**, jamás de su `repository`. Así cada módulo se puede extraer a un servicio aparte más adelante.
4. **`app/domain/` no importa FastAPI ni SQLAlchemy.** Son funciones puras sobre dataclasses: precios, tara, aplicación de pagos, saldos. Se testean sin levantar el servidor.
5. **Las integraciones viven detrás de una interfaz** en `app/integrations/`: `maps.py`, `push.py`, `storage.py`. Cambiar de proveedor no debe tocar ningún módulo.
6. **Los esquemas Pydantic son el contrato.** Toda entrada y toda salida tipadas. El cliente TS se regenera en CI; si cambia un campo, la app deja de compilar.
7. **Toda operación de dinero va en una transacción** y deja fila en `audit_log`.

## Roles

| Rol | Qué hace |
| --- | --- |
| `admin` | Todo: nota del día, pedidos, precios, clientes, pesada, carga, flota, rendición, impresiones, equipo, sucursales |
| `preventista` | Carga pedidos de sus clientes, pesa, carga el camión, entrega, cobra en la puerta, toca precios de sus pedidos |
| `cobrador` | **Rol nuevo**: sale a cobrar cuentas corrientes sin repartir. Ve clientes con saldo, registra cobros con foto del comprobante, rinde la caja al final del día. No ve pedidos que no sean suyos ni pantallas de pesada o carga |
| `cliente` | (Fase posterior) Catálogo, sus pedidos, seguimiento, cuenta corriente y envases |

El filtrado por rol se hace **en el servidor, en cada consulta**, nunca solo en la interfaz. Un preventista no puede leer ni modificar un pedido que no le asignaron; un cobrador solo ve las cuentas que se le asignaron.

La app es **una sola** para los cuatro roles, con un grupo de rutas de Expo Router por rol. Debe funcionar en celular Android y **también en escritorio en el navegador** (React Native Web), porque administración trabaja en la PC con teclado y pantalla grande.

## Modelo de datos

PostgreSQL, migraciones con Alembic. Decisiones fijas:

- **Claves primarias UUID** en todas las tablas. El teléfono del cliente es un índice único opcional, nunca la clave.
- **`sucursal_id` desde el día uno** en clientes, pedidos, cajones, cobros y cierres de caja. La empresa tiene granja + varias sucursales y todo reporte se filtra por sucursal.
- **Importes en `NUMERIC(12,2)`**, jamás `float`. La cuenta corriente pierde centavos con flotantes.
- **Fechas en `TIMESTAMPTZ`**, zona `America/Argentina/Mendoza`.
- **Campos flexibles en `JSONB`.**

Tablas mínimas: `sucursales`, `usuarios`, `clientes`, `precios_cliente`, `productos`, `listas_precio`, `pedidos`, `pedido_items`, `pedido_eventos`, `cajones`, `vehiculos`, `salidas`, `salida_track`, `pagos`, `comprobantes`, `movimientos_envases`, `cierres_caja`, `noticias`, `mensajes`, `audit_log`.

## Reglas de negocio (esto es lo que hay que respetar exacto)

**Productos y precios**
- 10 productos por corte: pollo entero, cuarto trasero, alas, pechuga, suprema, menudos, rancho, pechuga con alas, muslo, garras.
- Tres listas: mayorista, intermedio, minorista. El precio base es el del pollo entero mayorista.
- **Cada cliente tiene su precio propio por producto**, que pisa la lista. Sin precio propio, el renglón queda "sin precio" hasta que alguien lo tipea.
- Las listas se separan por **turno (mañana / tarde)** y por **zona**.
- Cualquier usuario del equipo puede corregir el precio de un renglón en el momento de cargar el pedido, con opción de guardarlo como precio propio del cliente.
- **Los precios y todos los totales se calculan siempre en el servidor.** La app nunca manda un total.

**Pedidos**
- El **número de pedido es el número de remito**: correlativo de 5 dígitos (`00012`), el mismo en la nota del día, el remito PDF, el Excel y la rendición.
- Los clientes piden **por cajas**, pero se cobra **por kilo**.
- Estados: `recibido` → `preparando` → `en_camino` → `entregado`, más `cancelado`.
- Un pedido lleva preventista, **segundo preventista** (van dos por camión), vehículo, zona, turno y fecha de reparto.
- Borrar un pedido borra sus cajones, deja auditoría y devuelve como saldo a favor lo ya cobrado.

**Pesada**
- Se pesa **bruto** y el sistema resta la **tara** (1,7 kg por cajón, configurable) para obtener el **neto**.
- Se puede cargar por lote (`N cajas` con un bruto total, el sistema reparte el neto y crea un cajón por caja) o cajón por cajón.
- **Cada cajón es una fila con id propia**: se anula con motivo, se marca cargado al camión, y un reintento con el mismo id no duplica.
- Al terminar de pesar se recalcula el total con el precio del cliente y se ajusta el saldo si el pedido ya estaba pagado.

**Carga y salida**
- La salida del día es un vehículo + hasta dos preventistas + hora de salida. Un preventista va en un solo vehículo por día.
- "Cerrar camión" avisa si falta pesar o cargar algo y pide motivo para salir igual; los pedidos pasan a `en_camino`.
- El repartidor comparte GPS: se manda cada 15 segundos o cada 25 metros de desplazamiento.

**Cobros**
- Medios: **efectivo, transferencia y cheque**. Sin pasarela de pago, sin QR.
- El cobro puede ser **mixto**: varias partes por medio distinto que suman el total.
- **Transferencia y cheque exigen foto del comprobante**, y una entrega no se cierra sin al menos una foto (comprobante o remito firmado). La foto se reduce en el celular antes de subir (máximo ~3,5 MB) y se guarda en object storage con URL firmada.
- **Cuenta corriente**: los pagos a cuenta se aplican a los pedidos más antiguos primero; el sobrante queda como saldo a favor y se descuenta del próximo pedido.
- **Cierre de caja** por persona y día: efectivo que debía rendir vs. recibido, diferencia, nota, quién y cuándo. Las transferencias y cheques se listan aparte y **no suman al efectivo a rendir**.
- **Envases (cajones adeudados)**: saldo por cliente, con movimientos de dejados y devueltos.

**Documentos**
- **Remito PDF**: 4 por hoja A4, proporciones de talonario 10 × 15 cm, con logo, datos fiscales, número correlativo, tabla KILOS · DETALLE · PRECIO X UN. · PRECIO TOTAL, CAJAS ADEUDADAS, SALDO de cuenta corriente, TOTAL y firma conforme.
- **Hoja de pedidos del día** (A4 apaisada) por turno y por preventista.
- **Hoja de ruta y rendición** por preventista, 26 pedidos por hoja, con columnas en blanco para efectivo / transferencia / cheque / saldo y cuadro de rendición.
- **Tickets de preparación** para comandera de 80 mm, uno por pedido, con un casillero por caja.
- **Consolidado en Excel** del día: una fila por pedido con número de remito, cliente, CUIT, detalle, cajones, kilos, saldo de cuenta corriente, cajas adeudadas y total.
- **Todos los PDF y Excel se generan en el servidor** (WeasyPrint o ReportLab + openpyxl), en el worker, y quedan archivados. La app los descarga, comparte con `expo-sharing` o imprime con `expo-print`.

## Offline

El repartidor en la calle es el caso de uso principal y suele trabajar sin señal.

- La base **SQLite local es la fuente de verdad de la pantalla**. La pesada se escribe local, se muestra al instante y se empuja cuando vuelve la conexión.
- Cola de mutaciones con **id generada en el cliente**; el servidor ignora duplicados por esa id. Reintento en orden, deteniéndose en el primer fallo de red para no desordenar.
- Un error de validación o de permiso **no se reintenta**: se muestra.
- Indicador visible de cuántas operaciones quedan pendientes de enviar.

## Tiempo real

WebSockets en FastAPI (no SSE: React Native no trae `EventSource`). Un canal por rol y por sucursal para: cambios de estado de pedidos, posición de los camiones, chat interno y noticias del equipo.

## Google Maps

- **En la app**: `react-native-maps` con Google Maps para el mapa embebido con camiones y paradas.
- **En el backend**: Directions API (ruta y ETA), **Routes API con optimización de paradas** (ordenar el reparto por recorrido más corto — es la función que el sistema viejo no tiene) y Geocoding API (dirección → coordenadas al dar de alta un cliente).
- **La API key vive solo en el servidor.** La app nunca llama a las APIs pagas de Google directamente. Cachear los resultados de geocoding en tabla. Poner límite de cuota desde el primer día.

## Sistema de diseño — "Molten Orange on Charcoal"

Industrial y cálido, pensado para operar bajo sol directo de Mendoza y con guantes puestos. Configurar estos tokens en `tailwind.config.js` de NativeWind y **no usar colores sueltos en los componentes**.

### Colores

```js
colors: {
  primary:        '#F74603',  // Molten Orange — acción principal, FAB, estado activo
  'primary-press':'#DD0200',  // Racing Red — estado presionado
  charcoal:       '#1A0706',  // Coffee Bean — barras, nav flotante, overlays
  cherry:         '#55100D',  // Black Cherry — cards oscuras
  background:     '#F4F2F1',  // Alabaster — fondo de trabajo
  surface:        '#F9F9F9',  // superficie de card
  'surface-white':'#FFFFFF',  // card elevada
  border:         '#E5E0DE',
  'on-surface':   '#1B1C1C',
  'on-surface-v': '#5C4038',
  success:        '#1E8E5A',  // entregado / cobrado
  pending:        '#646464',  // en depósito / encolado
  danger:         '#DD0200',  // deuda vencida, diferencia de peso, cancelación
}
```

**Nunca comunicar un estado solo con color**: cada estado lleva color + ícono + texto explícito.

### Tipografía

Familia **Inter**, con `fontFeatureSettings: '"tnum" 1'` (numerales tabulares) obligatorio en kilos, precios, totales y teléfonos, para que los números no bailen al actualizarse.

| Token | Tamaño / peso | Uso |
| --- | --- | --- |
| `display-metric` | 44px / 800, tracking -0.03em (32px en mobile) | Kilos totales, cantidad de cajones, plata del día |
| `headline-lg` | 28px / 700 (22px en mobile) | Título de pantalla |
| `headline-md` | 18px / 700 | Título de card |
| `body-lg` | 16px / 500 | Texto principal |
| `body-md` | 14px / 400 | Texto secundario |
| `body-metric` | 15px / 700 | Números dentro de listas |
| `label-caps` | 11px / 700, tracking 0.06em, mayúsculas | Encabezados de tabla, pasos del stepper, badges |
| `label-md` | 13px / 600 | Etiquetas de formulario |

### Formas, espaciado y elevación

- Base de 8pt (medios pasos de 4pt para tags compactos).
- Radios: cards y paneles **20–24px**; inputs y buscadores **16px**; botones y chips **pill (9999px)**; FAB círculo de **56×56px**.
- **Área táctil mínima absoluta de 48×48px** en todo elemento interactivo — el repartidor usa guantes o tiene las manos mojadas.
- Márgenes: 16px en mobile, 24px en tablet, 32px en escritorio. Padding inferior de 96px en mobile por la nav flotante y el FAB.
- Elevación: fondo plano sin sombra; card = borde 1px `#E5E0DE` + `0 4px 16px -2px rgba(26,7,6,0.06)`; card héroe = `0 8px 24px -4px rgba(26,7,6,0.12)`; nav flotante oscura = `0 12px 32px rgba(26,7,6,0.28)`; FAB = `0 8px 20px rgba(247,70,3,0.38)`.

### Layout por ancho

- **360–599px (celular)**: 4 columnas fluidas, contenido de borde a borde dentro de cards, nav inferior flotante oscura con FAB central.
- **600–1023px (tablet / montado en el camión)**: 8 columnas, los accesos rápidos pasan de grilla 2×2 a tira de 4.
- **1024px+ (escritorio de administración)**: 12 columnas, ancho máximo 1280px, **vista partida**: cola de pedidos a la izquierda (7 columnas), mapa en vivo y ficha del cliente a la derecha (5 columnas). Esta es la vista que usa administración todo el día: soportar teclado (Enter salta de campo, Ctrl+Enter confirma) y tablas densas con columnas fijas.

### Componentes a construir primero

- **Botón primario**: pill, `#F74603`, texto blanco 15px bold, alto 52px, ancho completo en mobile; presionado pasa a `#DD0200`.
- **Botón secundario oscuro**: fondo `#1A0706`, texto blanco. Para acciones administrativas ("Reasignar chofer").
- **Ghost**: sin borde, 14px bold naranja, fondo activo `rgba(247,70,3,0.08)`.
- **Stepper de 4 puntos**: `Cargado → Pesado → En reparto → Entregado`. Riel de 3px; puntos completos en verde o naranja con check; el paso activo pulsa con halo de 8px `rgba(247,70,3,0.2)`; pendientes en gris. Etiquetas en `label-caps` debajo.
- **Hero metric card**: radio 24px, variante oscura (fondo `#1A0706` con degradé interior `#55100D`) para tableros y variante clara para listas. Muestra la métrica grande ("1.420 kg", "$840.500") con chip de estado y etiqueta del camión ("Camión 04 • Reparto Norte").
- **Grilla 2×2 de accesos rápidos**: cuatro tiles de 20px de radio, ícono monocromo de 28px arriba a la izquierda, contador o directiva abajo ("Nuevo pedido", "Balanza", "Cobranzas", "Ruta GPS").
- **Order card**: superficie `#F9F9F9`, radio 20px, padding 16px. Arriba, nombre comercial del cliente y badge de estado (`entregado`, `en curso`, `deuda`). Al medio, cajones y kilos en negrita tabular ("24 cajones • 480,5 kg"). Abajo, botón de llamar y disparador de navegación a ancho completo.

### Tono de voz

Español rioplatense operativo, directo y corto: *"Cargado"*, *"Pesado"*, *"En reparto"*, *"Entregado"*, *"Cobrar saldo"*. Nada de lenguaje corporativo.

## Pantallas mínimas de la primera versión

**Repartidor / preventista**: Inicio de reparto (métrica del día + accesos rápidos) · Mis entregas (lista de order cards) · Entrega en curso (mapa, stepper, datos del cliente) · Registrar cobro (medios mixtos + cámara) · Pesada · Carga del camión · Cargar pedido.

**Cobrador**: Mis cuentas a cobrar (clientes con saldo, ordenados por zona) · Registrar cobro con foto · Cierre de caja del día.

**Administración**: Nota del día · Pedidos (lista densa con columnas y vista de tarjetas) · Cargar pedido · Clientes con precios propios y extracto · Listas de precios · Pesada · Carga · Flota en vivo · Rendición y cierre de caja · Imprimir · Equipo · Sucursales.

## Plan de trabajo

Trabajá por fases y **no avances de fase sin mostrar lo hecho y correr los tests**.

| Fase | Entregable |
| --- | --- |
| 0 | Monorepo, Docker Compose (Postgres + Redis), FastAPI con `/health`, Expo corriendo en web y Android, CI verde |
| 1 | `app/domain/` completo con sus tests en `pytest`: precios, tara y neto, aplicación de pagos, saldos, numeración de remitos |
| 2 | Esquema completo en Alembic + módulos `auth`, `sucursales`, `catalogo`, `clientes`. OpenAPI publicado y cliente TS generado |
| 3 | Módulos `pedidos`, `pesada`, `flota`. WebSockets. Semillas de datos de prueba |
| 4 | App del repartidor: las cuatro pantallas de campo, offline con SQLite local, cámara, Google Maps, push |
| 5 | Módulo `cobros` completo + rol cobrador + PDFs y Excel en el worker |
| 6 | Administración en escritorio (React Native Web): nota del día, pedidos, clientes, precios, rendición, impresiones |

## Cómo quiero que trabajes

- **Español** en el código de negocio (nombres de tablas, campos y endpoints), comentarios y commits. Inglés solo donde el framework lo imponga.
- Comentarios **solo donde la regla de negocio no sea obvia** (por qué la tara se resta antes de repartir el neto, por qué el pago se aplica al pedido más viejo). Nada de comentarios que repiten el código.
- **Test antes que endpoint** en todo lo que toque dinero, kilos o saldos.
- Commits chicos y con mensaje explicando el porqué, no el qué.
- Si una regla de negocio de este prompt te parece ambigua o contradictoria, **pará y preguntá** en vez de inventar. Es un sistema que maneja plata real.
- Nada de datos inventados en la interfaz: si un dato no existe todavía, estado vacío explícito.
- Al terminar cada fase, dejá en el README qué quedó hecho, qué falta y cómo levantar todo desde cero.
