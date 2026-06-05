# 🔄 Máquina de Estados Finitos (FSM) — DeliveryBot

> Referencia completa de la máquina de estados que controla el flujo de cada usuario.

---

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [Diagrama de Estados](#diagrama-de-estados)
- [Descripción de Estados](#descripción-de-estados)
- [Tabla de Transiciones](#tabla-de-transiciones)
- [Comportamiento de Reset](#comportamiento-de-reset)
- [Estados de Error y Recuperación](#estados-de-error-y-recuperación)
- [TTL de Sesión y Auto-Limpieza](#ttl-de-sesión-y-auto-limpieza)
- [Implementación en n8n](#implementación-en-n8n)

---

## Visión General

DeliveryBot implementa una **Máquina de Estados Finitos (FSM)** para controlar el flujo conversacional de cada usuario. Cada usuario tiene exactamente un estado en todo momento, almacenado en la hoja `SESSIONS` del Google Spreadsheet.

La FSM garantiza:

1. **Consistencia**: Cada mensaje se procesa en un contexto definido
2. **Predictibilidad**: El comportamiento del bot es determinista para cada combinación de estado + input
3. **Recuperabilidad**: Cualquier estado inválido se auto-corrige
4. **Aislamiento**: El estado de un usuario no afecta a otros

### Almacenamiento de Estado

```
SESSIONS sheet:
┌──────────────┬───────────┬────────────────┬───────────────┬──────────────────┬──────────────────┐
│ telegram_id  │ estado_fsm│ carrito_json   │ contexto_json │ ultimo_cambio    │ ttl_expira       │
├──────────────┼───────────┼────────────────┼───────────────┼──────────────────┼──────────────────┤
│ 100000001    │ MENU_PROD │ [{"id":"B.."}] │ {"cat":"Beb"} │ 2026-06-04T07:30 │ 2026-06-04T08:00 │
└──────────────┴───────────┴────────────────┴───────────────┴──────────────────┴──────────────────┘
```

---

## Diagrama de Estados

```
                              /start, /cancelar
                        ┌──────────────────────────┐
                        │                          │
                        ▼                          │
                   ┌─────────┐                     │
         ┌────────│  IDLE    │─────────┐           │
         │        └─────────┘         │           │
         │             │               │           │
    "Ver menú"    "Ver carrito"   "Ver estado"    │
         │             │               │           │
         ▼             ▼               ▼           │
    ┌──────────┐  ┌──────────┐  ┌──────────┐     │
    │ MENU_CAT │  │CARRITO_  │  │ ESTADO   │─────┘
    │          │  │VER       │  │          │
    └────┬─────┘  └────┬─────┘  └──────────┘
         │             │
    Seleccionar   ┌────┴────────────┐
    categoría     │                 │
         │    "Seguir       "Confirmar
         ▼    comprando"     pedido"
    ┌──────────┐  │                 │
    │ MENU_PROD│  │                 ▼
    │          │──┘          ┌──────────┐
    └────┬─────┘             │CONFIRMAR │
         │                   │          │
    Seleccionar              └────┬─────┘
    producto                      │
         │                   ┌────┴────┐
         ▼                   │         │
    ┌──────────┐          "Sí"      "No"
    │ MENU_QTY │             │         │
    │          │             ▼         │
    └────┬─────┘        ┌────────┐    │
         │              │PROCESAR│    │
    Seleccionar         │PEDIDO  │    │
    cantidad            └────┬───┘    │
         │                   │         │
         ▼                   ▼         │
    ┌──────────┐        ┌────────┐    │
    │ CARRITO_ │        │ IDLE   │◀───┘
    │ AGREGAR  │        │        │
    └────┬─────┘        └────────┘
         │
         ▼
    ┌──────────┐
    │CARRITO_  │
    │VER       │
    └──────────┘
```

---

## Descripción de Estados

### Estados Principales

| Estado | Descripción | Datos en `contexto_json` | Workflow |
|--------|-------------|--------------------------|----------|
| `IDLE` | Estado inicial/reposo. El usuario no tiene una interacción activa. Se muestra el menú principal con opciones. | `{}` | WF_MAIN_ROUTER |
| `MENU_CAT` | El usuario está viendo las categorías del menú (Bebidas, Almuerzos, Snacks). Espera selección de categoría. | `{}` | WF_FLOW_MENU |
| `MENU_PROD` | El usuario está viendo los productos de una categoría. Espera selección de producto. | `{"cat": "Bebidas"}` | WF_FLOW_MENU |
| `MENU_QTY` | El usuario seleccionó un producto y debe elegir la cantidad (1-5). | `{"cat": "Bebidas", "prod": "BEB-001"}` | WF_FLOW_MENU |
| `CARRITO_AGREGAR` | Estado transitorio. El producto se está agregando al carrito. Transiciona automáticamente a `CARRITO_VER`. | `{"added": "BEB-001", "qty": 2}` | WF_FLOW_CARRITO |
| `CARRITO_VER` | El usuario está viendo el contenido de su carrito con opciones para modificar, seguir comprando, o confirmar. | `{}` | WF_FLOW_CARRITO |
| `CONFIRMAR` | El usuario ve el resumen final del pedido y debe decidir si confirmar o cancelar. | `{}` | WF_FLOW_PEDIDO |
| `ESTADO` | El usuario está consultando el estado de sus pedidos activos o historial. | `{}` | WF_FLOW_ESTADO |

### Estados Transitorios (internos)

| Estado | Descripción | Duración |
|--------|-------------|----------|
| `PROCESANDO_PEDIDO` | El sistema está validando stock y generando el pedido. El usuario no puede interactuar. | < 3 segundos |
| `STOCK_VALIDACION` | Sub-estado de procesamiento: validando stock con optimistic locking. | < 1 segundo |

---

## Tabla de Transiciones

### Transiciones por Input del Usuario

| Estado Origen | Evento/Input | Estado Destino | Acción |
|---------------|-------------|----------------|--------|
| `IDLE` | Botón "🍽 Ver Menú" | `MENU_CAT` | Mostrar botones de categorías |
| `IDLE` | Botón "🛒 Mi Carrito" | `CARRITO_VER` | Mostrar contenido del carrito |
| `IDLE` | Botón "📦 Mis Pedidos" | `ESTADO` | Mostrar historial/tracking |
| `IDLE` | Texto libre | `IDLE` | Mostrar menú principal (ignorar texto) |
| `MENU_CAT` | Callback `cat_{categoria}` | `MENU_PROD` | Filtrar MENU por categoría, mostrar productos |
| `MENU_CAT` | Botón "⬅️ Volver" | `IDLE` | Mostrar menú principal |
| `MENU_PROD` | Callback `prod_{id}` | `MENU_QTY` | Mostrar selector de cantidad (1-5) |
| `MENU_PROD` | Botón "⬅️ Volver" | `MENU_CAT` | Mostrar categorías |
| `MENU_QTY` | Callback `qty_{n}` | `CARRITO_AGREGAR` | Agregar producto al carrito |
| `MENU_QTY` | Botón "⬅️ Volver" | `MENU_PROD` | Mostrar productos de la categoría |
| `CARRITO_AGREGAR` | (automático) | `CARRITO_VER` | Mostrar carrito actualizado |
| `CARRITO_VER` | Botón "🍽 Seguir comprando" | `MENU_CAT` | Mostrar categorías |
| `CARRITO_VER` | Botón "✅ Confirmar pedido" | `CONFIRMAR` | Mostrar resumen final |
| `CARRITO_VER` | Callback `cart_remove_{id}` | `CARRITO_VER` | Eliminar producto, mostrar carrito |
| `CARRITO_VER` | Botón "🗑 Vaciar carrito" | `IDLE` | Limpiar carrito, mostrar menú |
| `CONFIRMAR` | Botón "✅ Sí, confirmar" | `PROCESANDO_PEDIDO` → `IDLE` | Procesar pedido, notificar, volver a IDLE |
| `CONFIRMAR` | Botón "❌ No, volver" | `CARRITO_VER` | Mostrar carrito |
| `ESTADO` | Botón "⬅️ Volver" | `IDLE` | Mostrar menú principal |
| `ESTADO` | Callback `status_{id_pedido}` | `ESTADO` | Mostrar detalle del pedido seleccionado |

### Transiciones por Comandos Globales

Los comandos globales funcionan desde **cualquier estado**:

| Comando | Estado Destino | Acción |
|---------|----------------|--------|
| `/start` | `IDLE` | Reset completo: limpiar carrito (restaurar stock), limpiar contexto, mostrar menú principal |
| `/cancelar` | `IDLE` | Cancelar operación actual: si hay carrito, preguntar confirmación; si no, ir a IDLE |
| `/estado` | `ESTADO` | Ir directamente a consulta de pedidos sin perder carrito |
| `/ayuda` | *(sin cambio)* | Mostrar mensaje de ayuda sin cambiar estado |

### Transiciones por Eventos del Sistema

| Evento | Estado Origen | Estado Destino | Acción |
|--------|---------------|----------------|--------|
| TTL expirado | Cualquiera | (sesión eliminada) | Restaurar stock del carrito, eliminar sesión |
| Error de stock | `PROCESANDO_PEDIDO` | `CARRITO_VER` | Notificar producto agotado, actualizar carrito |
| Error de API | Cualquiera | *(sin cambio)* | Reintentar 3 veces, luego notificar error al usuario |
| Estado inválido | *(estado desconocido)* | `IDLE` | Auto-reset, log del error |

---

## Comportamiento de Reset

### Comando `/start`

El comando `/start` realiza un **reset completo** de la sesión del usuario:

```
1. Leer sesión actual del usuario
2. Si existe carrito con productos:
   a. Para cada producto en el carrito:
      - Restaurar stock en MENU (incrementar)
      - Incrementar version
   b. Limpiar carrito_json → []
3. Resetear estado_fsm → IDLE
4. Limpiar contexto_json → {}
5. Actualizar ultimo_cambio → now()
6. Actualizar ttl_expira → now() + SESSION_TTL_MIN
7. Enviar mensaje de bienvenida con menú principal
```

**Mensaje de bienvenida**:
```
👋 ¡Hola, {nombre}!

Bienvenido a DeliveryBot 🤖
Tu asistente de la cafetería.

¿Qué deseas hacer?

[🍽 Ver Menú] [🛒 Mi Carrito] [📦 Mis Pedidos]
```

### Comando `/cancelar`

El comando `/cancelar` tiene comportamiento contextual:

```
Si carrito está vacío:
  → Ir a IDLE, mostrar "No hay operación que cancelar"

Si carrito tiene productos:
  → Preguntar: "¿Deseas cancelar tu carrito actual con {n} productos?"
    → "Sí": Restaurar stock, limpiar carrito, ir a IDLE
    → "No": Volver al estado anterior
```

---

## Estados de Error y Recuperación

### Error: Estado FSM Inválido

Si el campo `estado_fsm` contiene un valor no reconocido (por edición manual del spreadsheet, corrupción, o bug), el sistema aplica **auto-sanación**:

```javascript
const VALID_STATES = [
  'IDLE', 'MENU_CAT', 'MENU_PROD', 'MENU_QTY',
  'CARRITO_AGREGAR', 'CARRITO_VER',
  'CONFIRMAR', 'PROCESANDO_PEDIDO',
  'ESTADO'
];

if (!VALID_STATES.includes(session.estado_fsm)) {
  // Log del estado inválido para diagnóstico
  await logError('INVALID_STATE', {
    telegram_id: session.telegram_id,
    invalid_state: session.estado_fsm
  });

  // Auto-sanación: reset a IDLE
  session.estado_fsm = 'IDLE';
  session.contexto_json = '{}';
  // Nota: NO se limpia el carrito (puede tener productos válidos)
}
```

### Error: Sesión No Encontrada

Si un usuario envía un mensaje pero no tiene sesión en `SESSIONS`:

```
1. Buscar en USUARIOS por telegram_id
2. Si existe: Crear nueva sesión con estado IDLE
3. Si no existe:
   a. Crear registro en USUARIOS (nombre, username de Telegram)
   b. Pedir departamento al usuario
   c. Crear sesión con estado IDLE
4. Mostrar menú principal
```

### Error: Carrito Corrupto

Si `carrito_json` contiene JSON inválido:

```
1. Registrar error en ERROR_LOG
2. Resetear carrito_json → '[]'
3. Notificar al usuario: "Tu carrito fue reiniciado por un error técnico"
4. Mantener estado actual (no forzar IDLE)
```

### Error: Producto en Carrito Ya No Existe

Si un producto en el carrito fue eliminado del menú:

```
1. Al mostrar carrito, verificar cada producto contra MENU
2. Si un producto no existe o está inactivo:
   a. Eliminarlo del carrito
   b. Notificar: "El producto {nombre} ya no está disponible y fue removido de tu carrito"
3. Recalcular totales
```

### Error: Conflicto de Stock (Optimistic Locking)

Si la validación de stock falla por conflicto de versión:

```
Intento 1: Leer stock=1, version=5 → Escribir → version≠5 → RETRY
Intento 2: Leer stock=0, version=6 → stock < qty → FALLO

Acción:
1. Eliminar producto agotado del carrito
2. Notificar: "Lo sentimos, {nombre} se agotó mientras preparábamos tu pedido"
3. Si quedan productos en carrito: Volver a CARRITO_VER
4. Si carrito está vacío: Ir a IDLE con mensaje "Tu carrito quedó vacío"
```

---

## TTL de Sesión y Auto-Limpieza

### Cálculo del TTL

Cada vez que se actualiza una sesión, se recalcula el TTL:

```javascript
const SESSION_TTL_MIN = 30; // Configurable

function updateSession(session, newState, newContext) {
  session.estado_fsm = newState;
  session.contexto_json = JSON.stringify(newContext);
  session.ultimo_cambio = new Date().toISOString();
  session.ttl_expira = new Date(
    Date.now() + SESSION_TTL_MIN * 60 * 1000
  ).toISOString();
}
```

### Proceso de Auto-Limpieza (`WF_SESSION_CLEANUP`)

Ejecutado vía CRON cada 15 minutos:

```
┌─────────────────────────────────────────────────────────────┐
│                   WF_SESSION_CLEANUP                         │
│                                                              │
│  1. Leer TODAS las filas de SESSIONS                        │
│                                                              │
│  2. Filtrar: ttl_expira < NOW()                             │
│                                                              │
│  3. Para cada sesión expirada:                              │
│     ┌───────────────────────────────────────────────────┐    │
│     │ a. ¿Tiene carrito con productos?                  │    │
│     │    SÍ → Para cada producto:                       │    │
│     │         - Leer stock actual de MENU               │    │
│     │         - Incrementar stock por cantidad           │    │
│     │         - Incrementar version                     │    │
│     │    NO → Continuar                                 │    │
│     │                                                   │    │
│     │ b. Eliminar fila de SESSIONS                      │    │
│     │                                                   │    │
│     │ c. Log: "Sesión de {telegram_id} limpiada.        │    │
│     │          Restaurados: {productos}" (si aplica)    │    │
│     └───────────────────────────────────────────────────┘    │
│                                                              │
│  4. Si se restauró stock de algún producto:                 │
│     → Invalidar caché de MENU (si se usa caché)             │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Escenarios de Expiración

| Escenario | Estado al expirar | Carrito | Acción |
|-----------|-------------------|---------|--------|
| Usuario abandonó en el menú | `MENU_*` | Vacío | Eliminar sesión |
| Usuario abandonó con carrito | `CARRITO_VER` | Con productos | Restaurar stock, eliminar sesión |
| Usuario abandonó confirmando | `CONFIRMAR` | Con productos | Restaurar stock, eliminar sesión |
| Usuario consultando pedidos | `ESTADO` | Puede tener | Si tiene carrito, restaurar stock |
| Sesión ya en IDLE | `IDLE` | Vacío | Eliminar sesión |

### Notificación al Usuario (Opcional)

Opcionalmente, se puede notificar al usuario antes de que su sesión expire:

```
Si ttl_expira - NOW() < 5 minutos AND tiene carrito con productos:
  → Enviar: "⏰ Tu carrito expirará en 5 minutos. 
             Envía cualquier mensaje para mantenerlo activo."
```

> **Nota**: Esta funcionalidad es opcional y aumenta el consumo de la API de Telegram. Se recomienda solo si la retención del carrito es importante para la operación.

---

## Implementación en n8n

### Nodo FSM Router

El router FSM se implementa como un nodo **Switch** en n8n que evalúa el campo `estado_fsm`:

```javascript
// Nodo Function: FSM Router
const state = $input.item.json.session.estado_fsm;
const isCommand = $input.item.json.message?.text?.startsWith('/');
const command = $input.item.json.message?.text;
const callbackData = $input.item.json.callback_query?.data;

// 1. Comandos globales (prioridad máxima)
if (command === '/start') return { route: 'RESET' };
if (command === '/cancelar') return { route: 'CANCELAR' };
if (command === '/estado') return { route: 'ESTADO' };
if (command === '/ayuda') return { route: 'AYUDA' };

// 2. Routing por estado FSM
switch (state) {
  case 'IDLE':
    return { route: 'MENU' };

  case 'MENU_CAT':
  case 'MENU_PROD':
  case 'MENU_QTY':
    return { route: 'MENU' };

  case 'CARRITO_AGREGAR':
  case 'CARRITO_VER':
    return { route: 'CARRITO' };

  case 'CONFIRMAR':
  case 'PROCESANDO_PEDIDO':
    return { route: 'PEDIDO' };

  case 'ESTADO':
    return { route: 'ESTADO' };

  default:
    // Auto-sanación
    await logError('INVALID_STATE', state);
    return { route: 'RESET' };
}
```

### Nodo de Actualización de Estado

Cada sub-workflow actualiza el estado al completar su lógica:

```javascript
// Nodo Function: Update Session State
const newState = 'MENU_PROD';
const newContext = { cat: 'Bebidas' };
const newCart = $input.item.json.session.carrito_json; // Sin cambios

const SESSION_TTL_MIN = 30;
const now = new Date();
const expira = new Date(now.getTime() + SESSION_TTL_MIN * 60000);

return {
  json: {
    telegram_id: $input.item.json.telegram_id,
    estado_fsm: newState,
    carrito_json: JSON.stringify(newCart),
    contexto_json: JSON.stringify(newContext),
    ultimo_cambio: now.toISOString(),
    ttl_expira: expira.toISOString()
  }
};
```

---

*Documento actualizado: 2026-06-04*
