# 🏗 Arquitectura del Sistema — DeliveryBot

> Documento técnico de referencia para la arquitectura de DeliveryBot.

---

## 📋 Tabla de Contenidos

- [Visión General](#visión-general)
- [Arquitectura de 3 Capas](#arquitectura-de-3-capas)
- [Flujo de Datos](#flujo-de-datos)
- [Diagrama de Interacción de APIs](#diagrama-de-interacción-de-apis)
- [Estrategia de Optimización de Google Sheets API](#estrategia-de-optimización-de-google-sheets-api)
- [Control de Concurrencia](#control-de-concurrencia)
- [Consideraciones de Escalabilidad](#consideraciones-de-escalabilidad)

---

## Visión General

DeliveryBot está diseñado como un sistema de 3 capas que utiliza servicios accesibles y de bajo costo para implementar un sistema de pedidos robusto para cafeterías institucionales.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                        ARQUITECTURA DELIVERYBOT                         │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────┐        ┌─────────────────┐        ┌─────────────────┐   │
│  │            │  HTTP   │                 │  HTTP   │                 │   │
│  │  Telegram  │◀──────▶│      n8n         │◀──────▶│  Google Sheets  │   │
│  │  Bot API   │ Webhook │  (Orquestador)  │ REST    │  API v4         │   │
│  │            │        │                 │        │                 │   │
│  └────────────┘        └─────────────────┘        └─────────────────┘   │
│   👤 Usuarios           ⚙️ Lógica de negocio       📊 Persistencia      │
│   📱 Interfaz           🔀 FSM Router              🗄 7 hojas/tablas    │
│   🔔 Notificaciones     📊 Reportes                🔒 Historial auto    │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### Principios de Diseño

1. **Simplicidad operativa**: Todas las herramientas tienen interfaz gráfica y son editables sin código
2. **Costo cero**: Todos los servicios usados tienen plan gratuito suficiente para la operación
3. **Resiliencia**: Auto-sanación de estados, restauración automática de stock, y logging de errores
4. **Extensibilidad**: Arquitectura modular basada en sub-workflows permite agregar funcionalidades sin tocar el flujo principal

---

## Arquitectura de 3 Capas

### Capa 1: Interfaz de Usuario (Telegram Bot API)

**Responsabilidad**: Interacción con el usuario final.

| Componente | Descripción |
|------------|-------------|
| **Menú principal** | Botones inline con categorías (Bebidas, Almuerzos, Snacks) |
| **Navegación de productos** | Lista de productos filtrada por categoría con precio y disponibilidad |
| **Selector de cantidad** | Botones numéricos (1-5) para seleccionar cantidad |
| **Vista del carrito** | Resumen formateado con emojis, subtotal, impuesto, y total |
| **Tracking de estado** | Barra de progreso visual con emojis por estado |
| **Historial** | Últimos 5 pedidos con resumen compacto |

**Protocolo de comunicación**:
- Telegram envía updates vía **webhook** (POST HTTP a n8n)
- n8n responde usando los métodos `sendMessage`, `editMessageText`, y `answerCallbackQuery` de la Bot API
- Los menús interactivos se construyen con `InlineKeyboardMarkup`
- Los callbacks llevan datos estructurados en `callback_data` (máximo 64 bytes)

**Formato de callback_data**:
```
{accion}_{id}
```
Ejemplos:
- `cat_Bebidas` — Seleccionar categoría Bebidas
- `prod_BEB-001` — Seleccionar producto BEB-001
- `qty_3` — Seleccionar cantidad 3
- `cart_remove_BEB-001` — Eliminar BEB-001 del carrito
- `confirm_yes` — Confirmar pedido
- `admin_prep_ORD-20260604-0001` — Admin: marcar como en preparación

### Capa 2: Motor de Orquestación (n8n)

**Responsabilidad**: Toda la lógica de negocio, routing, y coordinación.

n8n ejecuta **8 workflows** que colaboran entre sí:

```
                    ┌─────────────────────┐
     Webhook ──────▶│  WF_MAIN_ROUTER     │◀────── CRON (cada 15 min)
                    │  (FSM + routing)    │              │
                    └────────┬────────────┘     ┌────────┴──────────┐
                             │                  │ WF_SESSION_CLEANUP│
              ┌──────────────┼──────────────┐   └───────────────────┘
              │              │              │
     ┌────────▼──┐  ┌────────▼──┐  ┌────────▼──┐
     │WF_FLOW_   │  │WF_FLOW_   │  │WF_FLOW_   │
     │MENU       │  │CARRITO    │  │PEDIDO     │
     └───────────┘  └───────────┘  └───────────┘
                                           │
                                  ┌────────▼──────────┐
                                  │ WF_ADMIN_PANEL     │◀── Callback de cocina
                                  └───────────────────┘
                                           │
                                  ┌────────▼──────────┐
                                  │ WF_ADMIN_REPORTES  │◀── CRON (23:55 diario)
                                  └───────────────────┘
```

**Nodo Config (patrón compartido)**:

Cada workflow inicia con un nodo Function llamado "Config" que centraliza las constantes:

```javascript
// Nodo Config - presente en cada workflow
const CONFIG = {
  SPREADSHEET_ID: 'YOUR_SPREADSHEET_ID_HERE',
  ADMIN_CHAT_ID: '-100...',
  COCINA_GROUP_ID: '-100...',
  TAX_RATE: 0.08,
  SESSION_TTL_MIN: 30,
  BOT_NAME: 'DeliveryBot',
  MAX_QTY_PER_ITEM: 5,
  MAX_CART_ITEMS: 10,
  ORDER_ID_PREFIX: 'ORD'
};

return { json: CONFIG };
```

### Capa 3: Persistencia de Datos (Google Sheets)

**Responsabilidad**: Almacenamiento y consulta de todos los datos.

**Estructura del Spreadsheet** (`DeliveryBot_DB`):

```
DeliveryBot_DB (Spreadsheet)
├── MENU              → Catálogo de productos (lectura frecuente, escritura al actualizar stock)
├── PEDIDOS           → Registro maestro de pedidos (append-only + update de estado)
├── USUARIOS          → Perfil de usuarios (lectura frecuente, escritura en registro)
├── SESSIONS          → Estado FSM (lectura/escritura en cada interacción)
├── DETALLE_LINEAS    → Líneas de pedido normalizadas (append-only)
├── REPORTES_CACHE    → Caché de reportes diarios (append-only)
└── ERROR_LOG         → Log de errores (append-only)
```

**Patrones de acceso por hoja**:

| Hoja | Lectura | Escritura | Patrón |
|------|---------|-----------|--------|
| MENU | Cada navegación de menú | Al confirmar pedido (stock) | Read-heavy |
| PEDIDOS | Al consultar estado | Al crear/actualizar pedido | Balanced |
| USUARIOS | Al crear sesión | Al registrar nuevo usuario | Read-heavy |
| SESSIONS | Cada mensaje entrante | Cada cambio de estado | Read-Write intensive |
| DETALLE_LINEAS | En reportes | Al confirmar pedido | Write-heavy |
| REPORTES_CACHE | Bajo demanda | Una vez al día | Minimal |
| ERROR_LOG | Debug manual | Al ocurrir errores | Write-only |

---

## Flujo de Datos

### Flujo Principal: Pedido Completo

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  /start  │───▶│ Navegar  │───▶│ Agregar  │───▶│Confirmar │───▶│  Cocina  │
│          │    │  menú    │    │ al carro │    │  pedido  │    │ prepara  │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
     │               │               │               │               │
     ▼               ▼               ▼               ▼               ▼
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Crear    │    │ Leer     │    │ Actualizar│   │ Validar  │    │ Update   │
│ SESSION  │    │ MENU     │    │ SESSION   │   │ stock +  │    │ PEDIDOS  │
│          │    │ sheet    │    │ (carrito) │   │ Escribir │    │ (estado) │
│          │    │          │    │          │    │ PEDIDOS  │    │          │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
```

### Detalle: Confirmación de Pedido (Paso Crítico)

Este es el flujo más complejo, ya que involucra validación de stock con control de concurrencia:

```
1. LEER carrito de SESSION
         │
2. Para CADA producto en carrito:
         │
         ├── LEER fila de MENU (stock actual + version)
         │
         ├── ¿stock >= cantidad solicitada?
         │     │
         │     ├── SÍ: Continuar
         │     │
         │     └── NO: Notificar usuario → Eliminar del carrito
         │
         └── ¿version == version_esperada?
               │
               ├── SÍ: Continuar
               │
               └── NO: Re-leer stock → Reintentar (max 3 intentos)
                         │
                         └── Si falla: STOCK_CONFLICT → ERROR_LOG
         │
3. Generar ID de pedido único
         │
4. BATCH WRITE:
         ├── Decrementar stock + incrementar version en MENU
         ├── Append pedido en PEDIDOS
         ├── Append líneas en DETALLE_LINEAS
         └── Limpiar carrito en SESSION
         │
5. Notificar:
         ├── Usuario: "Pedido ORD-... confirmado ✅"
         └── Cocina: "🔔 Nuevo pedido de Andrea López..."
```

---

## Diagrama de Interacción de APIs

### Request Flow: Usuario envía mensaje

```
                  Telegram                n8n                 Google Sheets
                  Cloud                   Server              API
                    │                       │                      │
 User sends msg ───▶│                       │                      │
                    │──── POST /webhook ───▶│                      │
                    │                       │                      │
                    │                       │── GET SESSIONS ──────▶│
                    │                       │◀── Session data ──────│
                    │                       │                      │
                    │                       │── [FSM routing] ──── │
                    │                       │                      │
                    │                       │── GET MENU ──────────▶│
                    │                       │◀── Menu data ────────│
                    │                       │                      │
                    │                       │── PUT SESSIONS ──────▶│
                    │                       │◀── OK ───────────────│
                    │                       │                      │
                    │◀── sendMessage ───────│                      │
                    │                       │                      │
 User sees reply ◀─│                       │                      │
                    │                       │                      │
```

### Request Flow: Confirmación de Pedido

```
                  Telegram                n8n                 Google Sheets
                    │                       │                      │
 User clicks       │                       │                      │
 "Confirmar" ─────▶│                       │                      │
                    │── POST /webhook ─────▶│                      │
                    │                       │                      │
                    │                       │── GET SESSIONS ──────▶│
                    │                       │◀── Carrito data ─────│
                    │                       │                      │
                    │                       │── GET MENU (batch) ──▶│
                    │                       │◀── Stock + versions ─│
                    │                       │                      │
                    │                       │── [Validate stock] ──│
                    │                       │── [Generate order ID]│
                    │                       │                      │
                    │                       │── BATCH WRITE: ──────▶│
                    │                       │   - Update MENU      │
                    │                       │   - Append PEDIDOS   │
                    │                       │   - Append DETALLE   │
                    │                       │   - Clear SESSION    │
                    │                       │◀── OK ───────────────│
                    │                       │                      │
                    │◀── sendMessage ───────│ (user confirmation)  │
                    │                       │                      │
  Cocina group ◀───│◀── sendMessage ───────│ (kitchen notif)      │
                    │                       │                      │
```

---

## Estrategia de Optimización de Google Sheets API

### Problema: Cuotas de API

Google Sheets API tiene las siguientes cuotas en el plan gratuito:

| Cuota | Límite |
|-------|--------|
| Lecturas por minuto | 60 |
| Escrituras por minuto | 60 |
| Lecturas por día | 300 (por usuario) |
| Requests por 100 segundos | 100 |

Con un flujo de pedido completo que requiere ~6-10 llamadas a la API, una cafetería con 50 pedidos/hora rápidamente excedería las cuotas.

### Solución 1: Batch Reads (Lecturas por lote)

En lugar de leer cada hoja individualmente, usar `spreadsheets.values.batchGet` para leer múltiples rangos en una sola llamada:

```javascript
// ❌ MALO: 3 llamadas a la API
const menu = await sheets.get('MENU!A:I');
const session = await sheets.get('SESSIONS!A:F');
const user = await sheets.get('USUARIOS!A:G');

// ✅ BUENO: 1 llamada a la API
const batchResult = await sheets.batchGet({
  ranges: ['MENU!A:I', 'SESSIONS!A:F', 'USUARIOS!A:G']
});
```

**Implementación en n8n**: Usar el nodo "HTTP Request" directamente contra la API REST de Google Sheets en lugar del nodo nativo de Google Sheets, que solo soporta operaciones individuales.

### Solución 2: Batch Writes (Escrituras por lote)

Usar `spreadsheets.values.batchUpdate` para agrupar múltiples escrituras:

```javascript
// ❌ MALO: 4 llamadas a la API
await sheets.update('MENU!F2', newStock);       // Actualizar stock
await sheets.update('MENU!I2', newVersion);     // Actualizar version
await sheets.append('PEDIDOS', orderRow);        // Agregar pedido
await sheets.append('DETALLE_LINEAS', lines);    // Agregar líneas

// ✅ BUENO: 1 llamada a la API
await sheets.batchUpdate({
  data: [
    { range: 'MENU!F2', values: [[newStock]] },
    { range: 'MENU!I2', values: [[newVersion]] },
    // ... más updates
  ]
});
// + 1 llamada para appends
await sheets.batchAppend({ /* ... */ });
```

### Solución 3: Caché en Memoria

Para datos que cambian infrecuentemente (como el menú), mantener un caché en memoria dentro del workflow de n8n:

```javascript
// Patrón de caché usando Static Data de n8n
const staticData = $getWorkflowStaticData('global');

// Verificar si el caché es válido
const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutos
const now = Date.now();

if (!staticData.menuCache || (now - staticData.menuCacheTime) > CACHE_TTL_MS) {
  // Cache miss o expirado: leer de Google Sheets
  staticData.menuCache = await readMenuFromSheets();
  staticData.menuCacheTime = now;
}

return staticData.menuCache;
```

**Datos cacheables**:

| Dato | TTL recomendado | Razón |
|------|----------------|-------|
| MENU (productos) | 5 minutos | Cambia poco frecuentemente |
| USUARIOS (perfil) | 10 minutos | Casi nunca cambia |
| SESSIONS | No cachear | Cambia en cada interacción |
| PEDIDOS | No cachear | Debe ser siempre actual |

### Solución 4: Rate Limiting Inteligente

Implementar un limitador de velocidad para evitar exceder las cuotas:

```javascript
// Patrón de rate limiting con backoff exponencial
const staticData = $getWorkflowStaticData('global');

async function rateLimitedRequest(fn) {
  const MIN_INTERVAL_MS = 1100; // ~55 req/min (bajo el límite de 60)
  const lastCall = staticData.lastApiCall || 0;
  const elapsed = Date.now() - lastCall;

  if (elapsed < MIN_INTERVAL_MS) {
    await sleep(MIN_INTERVAL_MS - elapsed);
  }

  try {
    const result = await fn();
    staticData.lastApiCall = Date.now();
    return result;
  } catch (error) {
    if (error.code === 429) {
      // Rate limited: esperar con backoff exponencial
      const retryAfter = (error.retryAfter || 60) * 1000;
      await sleep(retryAfter);
      return rateLimitedRequest(fn); // Reintentar
    }
    throw error;
  }
}
```

### Resumen de Optimizaciones

| Estrategia | Reducción de API calls | Complejidad |
|------------|----------------------|-------------|
| Batch Reads | 50-60% | Media |
| Batch Writes | 40-50% | Media |
| Caché en memoria | 30-40% | Baja |
| Rate limiting | Previene 429s | Baja |
| **Combinadas** | **~75-80%** | **Media** |

---

## Control de Concurrencia

### El Problema

Google Sheets no soporta transacciones ACID. Cuando dos usuarios intentan ordenar el último item de un producto simultáneamente, ambos podrían leer stock=1, y ambos decrementarlo a 0, resultando en **overselling** (vender más stock del disponible).

```
Tiempo    Usuario A                  Google Sheets              Usuario B
──────    ─────────                  ──────────────              ─────────
t1        Lee stock(BEB-001) = 1                                
t2                                                              Lee stock(BEB-001) = 1
t3        stock >= 1? ✅ SÍ                                    
t4                                                              stock >= 1? ✅ SÍ
t5        Escribe stock = 0                                     
t6                                                              Escribe stock = 0
                                                                 ← ¡OVERSELLING!
                                     stock = 0 pero se
                                     vendieron 2 unidades
```

### La Solución: Optimistic Locking

Implementamos **bloqueo optimista** usando un campo `version` en la hoja MENU:

```
Tiempo    Usuario A                  Google Sheets              Usuario B
──────    ─────────                  ──────────────              ─────────
t1        Lee stock=1, version=5                                 
t2                                                              Lee stock=1, version=5
t3        ¿version aún es 5?                                    
t4        SÍ → stock=0, version=6                               
t5                                                              ¿version aún es 5?
t6                                                              NO (version=6) → RETRY
t7                                                              Lee stock=0, version=6
t8                                                              stock >= 1? ❌ NO
t9                                                              "Producto agotado" 🚫
```

### Implementación en n8n

```javascript
// Pseudo-código del nodo de validación de stock
const MAX_RETRIES = 3;

async function validateAndReserveStock(cartItems) {
  for (const item of cartItems) {
    let retries = 0;
    let success = false;

    while (retries < MAX_RETRIES && !success) {
      // 1. Leer estado actual
      const row = await readMenuRow(item.id_producto);
      const currentStock = row.stock;
      const currentVersion = row.version;

      // 2. Validar disponibilidad
      if (currentStock < item.qty) {
        throw new Error(`Stock insuficiente para ${item.nombre}`);
      }

      // 3. Intentar actualizar con check de versión
      const updated = await conditionalUpdate(
        item.id_producto,
        {
          stock: currentStock - item.qty,
          version: currentVersion + 1
        },
        currentVersion  // Condición: solo actualizar si version == currentVersion
      );

      if (updated) {
        success = true;
      } else {
        retries++;
        // Espera breve antes de reintentar
        await sleep(100 * Math.pow(2, retries));
      }
    }

    if (!success) {
      // Registrar conflicto en ERROR_LOG
      await logError('STOCK_CONFLICT', item.id_producto);
      throw new Error(`No se pudo reservar stock para ${item.nombre}`);
    }
  }
}
```

### Implementación del Conditional Update

Dado que Google Sheets no soporta "UPDATE WHERE version = X", implementamos el check en el código de n8n:

```javascript
async function conditionalUpdate(productId, newValues, expectedVersion) {
  // 1. Re-leer la fila justo antes de escribir
  const currentRow = await readMenuRow(productId);

  // 2. Verificar que la versión no cambió
  if (currentRow.version !== expectedVersion) {
    return false; // Alguien más modificó el stock
  }

  // 3. Escribir los nuevos valores (incluido version+1)
  await updateMenuRow(productId, newValues);
  return true;
}
```

> ⚠️ **Nota**: Esta implementación tiene una ventana de vulnerabilidad entre el paso 1 (re-lectura) y el paso 3 (escritura). En un sistema de base de datos real, esto sería una transacción atómica. Para Google Sheets, esta ventana es aceptablemente pequeña (~50-100ms) dado el volumen esperado de una cafetería institucional (<100 pedidos/hora).

### Restauración de Stock por Carritos Abandonados

Cuando una sesión expira con productos en el carrito, el stock debe restaurarse:

```javascript
// Ejecutado por WF_SESSION_CLEANUP cada 15 minutos
async function cleanupExpiredSessions() {
  const sessions = await readAllSessions();
  const now = new Date();

  for (const session of sessions) {
    if (new Date(session.ttl_expira) < now) {
      // Restaurar stock de productos en el carrito abandonado
      if (session.carrito_json) {
        const cart = JSON.parse(session.carrito_json);
        for (const item of cart) {
          await incrementStock(item.id_producto, item.qty);
        }
      }

      // Eliminar la sesión expirada
      await deleteSession(session.telegram_id);
    }
  }
}
```

---

## Consideraciones de Escalabilidad

### Límites Actuales (Google Sheets)

| Parámetro | Límite | Impacto |
|-----------|--------|---------|
| Filas por hoja | 10,000,000 | Sin impacto a corto plazo |
| Celdas por spreadsheet | 10,000,000 | ~1.4M pedidos antes de alcanzar límite |
| API calls por minuto | 60 read / 60 write | ~30 pedidos/minuto máximo |
| Tamaño de celda | 50,000 caracteres | Sin impacto (JSON de carrito ~500 chars) |

### Cuándo Migrar

Se recomienda migrar a una base de datos real cuando:

- [ ] El volumen exceda **50 pedidos por hora** consistentemente
- [ ] El spreadsheet alcance **50,000 filas** en PEDIDOS
- [ ] Se requieran **queries complejas** (JOINs, agregaciones en tiempo real)
- [ ] Se necesite **concurrencia real** con transacciones ACID
- [ ] Se integren **pagos digitales** (requiere mayor seguridad)

### Ruta de Migración

```
Google Sheets (actual)
       │
       ▼
Supabase (PostgreSQL) ── Opción recomendada
       │                  - API REST automática
       │                  - Auth integrado
       │                  - Realtime subscriptions
       │                  - Plan gratuito generoso
       ▼
PostgreSQL dedicado ───── Para alto volumen
                          - Control total
                          - Hosting propio o cloud
```

La migración se facilita porque:
1. El modelo de datos ya es relacional (normalizado con PKs y FKs)
2. Los queries son simples (búsqueda por PK, filtros por fecha/estado)
3. Los sub-workflows se modifican solo en los nodos de datos, no en la lógica

---

*Documento actualizado: 2026-06-04*
