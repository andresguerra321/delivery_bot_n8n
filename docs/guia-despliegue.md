# 🚀 Guía de Despliegue — DeliveryBot

> Guía paso a paso para desplegar DeliveryBot desde cero en un entorno de producción.

---

## 📋 Tabla de Contenidos

- [Checklist de Requisitos Previos](#checklist-de-requisitos-previos)
- [Paso 1: Configurar Google Cloud y Sheets API](#paso-1-configurar-google-cloud-y-sheets-api)
- [Paso 2: Crear el Bot de Telegram](#paso-2-crear-el-bot-de-telegram)
- [Paso 3: Instalar n8n con Docker](#paso-3-instalar-n8n-con-docker)
- [Paso 4: Configurar el Google Spreadsheet](#paso-4-configurar-el-google-spreadsheet)
- [Paso 5: Importar y Configurar Workflows](#paso-5-importar-y-configurar-workflows)
- [Paso 6: Configurar Credenciales en n8n](#paso-6-configurar-credenciales-en-n8n)
- [Paso 7: Activar Workflows](#paso-7-activar-workflows)
- [Paso 8: Testing y Verificación](#paso-8-testing-y-verificación)
- [Problemas Comunes y Soluciones](#problemas-comunes-y-soluciones)

---

## Checklist de Requisitos Previos

Antes de comenzar, verifica que tengas lo siguiente:

### Cuentas y Accesos

- [ ] **Cuenta de Google** (Gmail) con acceso a Google Cloud Console
- [ ] **Cuenta de Telegram** con la app instalada
- [ ] **Servidor o VPS** con acceso SSH (para n8n self-hosted) **O** cuenta de n8n Cloud
- [ ] **Dominio con SSL** (para webhook de producción) **O** ngrok (para desarrollo)

### Software (para n8n self-hosted)

- [ ] **Docker** v20.10 o superior
- [ ] **Docker Compose** v2.0 o superior
- [ ] **Git** (opcional, para clonar el repositorio)

### Conocimientos

- [ ] Familiaridad básica con Telegram
- [ ] Conocimiento básico de Google Sheets
- [ ] Capacidad de ejecutar comandos en terminal

---

## Paso 1: Configurar Google Cloud y Sheets API

### 1.1 Crear o seleccionar proyecto en Google Cloud

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Click en el selector de proyecto (arriba a la izquierda)
3. Click en **"Nuevo Proyecto"**
4. Configurar:
   - **Nombre del proyecto**: `DeliveryBot`
   - **Organización**: (dejar por defecto o seleccionar tu organización)
   - **Ubicación**: (dejar por defecto)
5. Click en **"Crear"**
6. Esperar a que el proyecto se cree y seleccionarlo como proyecto activo

### 1.2 Habilitar la API de Google Sheets

1. En Google Cloud Console, ir a **APIs & Services → Library**
2. En el buscador, escribir: `Google Sheets API`
3. Click en **"Google Sheets API"** en los resultados
4. Click en **"Habilitar"** (botón azul)
5. Esperar a que se habilite (~30 segundos)

> **Nota**: También necesitas **Google Drive API** habilitada para los permisos de archivos:
> - Buscar `Google Drive API` en la Library
> - Click en **"Habilitar"**

### 1.3 Crear una Cuenta de Servicio

1. Ir a **APIs & Services → Credentials**
2. Click en **"+ Crear Credenciales"** (arriba)
3. Seleccionar **"Cuenta de Servicio"**
4. Configurar:
   - **Nombre**: `deliverybot-sheets`
   - **ID**: `deliverybot-sheets` (se auto-genera)
   - **Descripción**: `Cuenta de servicio para DeliveryBot - acceso a Google Sheets`
5. Click en **"Crear y continuar"**
6. **Rol**: Seleccionar `Básico → Editor` (o dejarlo sin rol, el acceso se da vía compartir el sheet)
7. Click en **"Continuar"**
8. Click en **"Listo"**

### 1.4 Generar clave JSON

1. En la lista de cuentas de servicio, click en la que acabas de crear (`deliverybot-sheets`)
2. Ir a la pestaña **"Claves"**
3. Click en **"Agregar clave → Crear clave nueva"**
4. Seleccionar formato **JSON**
5. Click en **"Crear"**
6. Se descargará un archivo `deliverybot-XXXX.json`. **Guardar este archivo de forma segura**.

> ⚠️ **IMPORTANTE**: Este archivo contiene credenciales sensibles. No lo subas a repositorios públicos, no lo compartas, y guárdalo en un lugar seguro.

### 1.5 Verificar el email de la cuenta de servicio

El archivo JSON contiene un campo `client_email` como:
```
deliverybot-sheets@deliverybot-XXXXX.iam.gserviceaccount.com
```

**Copia este email**, lo necesitarás para compartir el spreadsheet en el Paso 4.

---

## Paso 2: Crear el Bot de Telegram

### 2.1 Crear el bot con BotFather

1. Abrir Telegram y buscar [@BotFather](https://t.me/BotFather)
2. Enviar: `/start` (si es la primera vez)
3. Enviar: `/newbot`
4. BotFather preguntará el **nombre visible** del bot:
   ```
   DeliveryBot Cafetería
   ```
5. BotFather preguntará el **username** del bot (debe terminar en `bot`):
   ```
   deliverybot_cafe_bot
   ```
6. BotFather responderá con el **token de acceso**:
   ```
   Done! Congratulations on your new bot. You will find it at t.me/deliverybot_cafe_bot.
   
   Use this token to access the HTTP API:
   7123456789:AAH1bGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
   ```

> 📝 **Copia y guarda el token**. Lo necesitarás para configurar n8n.

### 2.2 Configurar comandos del bot

Enviar a BotFather:
```
/setcommands
```

Seleccionar tu bot, luego enviar la lista de comandos:
```
start - Iniciar o reiniciar el bot
cancelar - Cancelar operación actual
estado - Ver estado de mi pedido
ayuda - Mostrar ayuda
```

### 2.3 Configurar descripción

Enviar a BotFather:
```
/setdescription
```

Seleccionar tu bot, luego enviar:
```
🍽 Sistema de pedidos de la cafetería institucional.
Realiza tus pedidos sin filas.
Envía /start para comenzar.
```

### 2.4 Configurar "About" (texto corto)

Enviar a BotFather:
```
/setabouttext
```

Seleccionar tu bot, luego enviar:
```
Bot de pedidos de cafetería 🤖☕
```

### 2.5 Configurar foto de perfil (opcional)

1. Enviar a BotFather: `/setuserpic`
2. Seleccionar tu bot
3. Enviar una imagen cuadrada (mínimo 512x512 px) con el logo de la cafetería

### 2.6 Crear grupos de Telegram

Necesitas crear **dos grupos**:

#### Grupo de Cocina
1. Crear un grupo en Telegram llamado "🍳 Cocina - DeliveryBot"
2. Agregar el bot al grupo
3. Obtener el ID del grupo:
   - Agregar [@RawDataBot](https://t.me/RawDataBot) al grupo temporalmente
   - Enviar cualquier mensaje en el grupo
   - RawDataBot responderá con un JSON que incluye el `chat_id` (número negativo)
   - Copiar el `chat_id` (ej: `-1001234567890`)
   - **Remover** @RawDataBot del grupo

#### Grupo de Administradores
1. Crear un grupo en Telegram llamado "📊 Admin - DeliveryBot"
2. Agregar el bot al grupo
3. Obtener el `chat_id` del mismo modo que el grupo de cocina

---

## Paso 3: Instalar n8n con Docker

### 3.1 Opción A: Docker Compose (Recomendado)

Crear un directorio para n8n y el archivo `docker-compose.yml`:

```bash
mkdir -p ~/n8n-deliverybot
cd ~/n8n-deliverybot
```

Crear el archivo `docker-compose.yml`:

```yaml
version: '3.8'

services:
  n8n:
    image: docker.n8n.io/n8nio/n8n:latest
    container_name: n8n-deliverybot
    restart: unless-stopped
    ports:
      - "5678:5678"
    environment:
      # Configuración general
      - N8N_HOST=tu-dominio.com
      - N8N_PORT=5678
      - N8N_PROTOCOL=https
      - WEBHOOK_URL=https://tu-dominio.com/
      
      # Zona horaria
      - GENERIC_TIMEZONE=America/Mexico_City
      - TZ=America/Mexico_City
      
      # Autenticación de la interfaz de n8n
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=tu_password_seguro
      
      # Base de datos (SQLite por defecto, suficiente para DeliveryBot)
      - DB_TYPE=sqlite
      - DB_SQLITE_VACUUM_ON_STARTUP=true
      
      # Ejecuciones
      - EXECUTIONS_DATA_SAVE_ON_ERROR=all
      - EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
      - EXECUTIONS_DATA_SAVE_MANUAL_EXECUTIONS=true
    volumes:
      - n8n_data:/home/node/.n8n
    healthcheck:
      test: ["CMD-SHELL", "wget -qO- http://localhost:5678/healthz || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  n8n_data:
    driver: local
```

Iniciar n8n:

```bash
docker compose up -d
```

Verificar que está corriendo:

```bash
docker compose logs -f n8n
# Buscar: "n8n ready on 0.0.0.0, port 5678"
```

### 3.2 Opción B: Docker Run (Rápido)

```bash
docker run -d \
  --name n8n-deliverybot \
  --restart unless-stopped \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e GENERIC_TIMEZONE=America/Mexico_City \
  -e TZ=America/Mexico_City \
  docker.n8n.io/n8nio/n8n:latest
```

### 3.3 Opción C: n8n Cloud

1. Ir a [n8n.cloud](https://n8n.cloud)
2. Crear una cuenta
3. Seguir el wizard de configuración
4. La URL del webhook será proporcionada automáticamente (ej: `https://tu-org.app.n8n.cloud/webhook/...`)

### 3.4 Configurar acceso HTTPS (self-hosted)

Para producción, necesitas HTTPS para el webhook de Telegram. Opciones:

#### Opción A: Reverse Proxy con Nginx + Let's Encrypt

```bash
# Instalar Nginx y Certbot
sudo apt install nginx certbot python3-certbot-nginx

# Configurar Nginx
sudo nano /etc/nginx/sites-available/n8n
```

Contenido del archivo Nginx:

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        chunked_transfer_encoding on;
    }
}
```

```bash
# Activar el sitio
sudo ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Obtener certificado SSL
sudo certbot --nginx -d tu-dominio.com
```

#### Opción B: ngrok (solo desarrollo)

```bash
# Instalar ngrok
# https://ngrok.com/download

# Exponer n8n
ngrok http 5678

# Usar la URL HTTPS generada (ej: https://abc123.ngrok.io)
```

### 3.5 Verificar instalación

1. Abrir el navegador en `https://tu-dominio.com` (o `http://localhost:5678` para desarrollo)
2. Crear una cuenta de administrador de n8n (primera vez)
3. Verificar que la interfaz de n8n carga correctamente

---

## Paso 4: Configurar el Google Spreadsheet

### 4.1 Crear el Spreadsheet

1. Ir a [Google Sheets](https://sheets.google.com)
2. Click en **"+ Nuevo"** → **"Google Sheets"** → **"Hoja de cálculo en blanco"**
3. Renombrar a: **`DeliveryBot_DB`**

### 4.2 Crear las hojas (tabs)

Crear las siguientes 7 hojas renombrando la hoja existente y agregando nuevas:

1. Renombrar "Hoja 1" a **`MENU`**
2. Agregar hoja: **`PEDIDOS`**
3. Agregar hoja: **`USUARIOS`**
4. Agregar hoja: **`SESSIONS`**
5. Agregar hoja: **`DETALLE_LINEAS`**
6. Agregar hoja: **`REPORTES_CACHE`**
7. Agregar hoja: **`ERROR_LOG`**

### 4.3 Agregar headers a cada hoja

#### MENU
```
A1: id_producto | B1: nombre | C1: descripcion | D1: precio | E1: categoria | F1: stock | G1: stock_minimo | H1: activo | I1: version
```

#### PEDIDOS
```
A1: id_pedido | B1: telegram_id | C1: detalles_pedido | D1: subtotal | E1: impuesto | F1: total_pago | G1: estado | H1: fecha | I1: hora | J1: hora_entrega | K1: notas
```

#### USUARIOS
```
A1: telegram_id | B1: nombre_completo | C1: username | D1: departamento | E1: puntos_lealtad | F1: fecha_registro | G1: activo
```

#### SESSIONS
```
A1: telegram_id | B1: estado_fsm | C1: carrito_json | D1: contexto_json | E1: ultimo_cambio | F1: ttl_expira
```

#### DETALLE_LINEAS
```
A1: id_pedido | B1: id_producto | C1: nombre | D1: cantidad | E1: precio_unitario | F1: fecha
```

#### REPORTES_CACHE
```
A1: fecha | B1: total_ventas | C1: num_pedidos | D1: producto_estrella | E1: cantidad_estrella | F1: hora_pico | G1: generado_en
```

#### ERROR_LOG
```
A1: timestamp | B1: telegram_id | C1: tipo_error | D1: detalle | E1: resuelto
```

### 4.4 Poblar datos de prueba

1. Abrir el archivo `sheets/MENU_sample.csv` del repositorio
2. Copiar los datos (sin la fila de headers) a la hoja `MENU`, comenzando en la fila 2
3. Opcionalmente, poblar `USUARIOS`, `PEDIDOS`, y `DETALLE_LINEAS` con los datos de los archivos `*_template.csv`

### 4.5 Compartir con la cuenta de servicio

1. En el Spreadsheet, click en **"Compartir"** (botón verde arriba a la derecha)
2. En el campo "Agregar personas", pegar el email de la cuenta de servicio:
   ```
   deliverybot-sheets@deliverybot-XXXXX.iam.gserviceaccount.com
   ```
3. Seleccionar permiso: **"Editor"**
4. Desmarcar "Notificar a las personas"
5. Click en **"Compartir"**

### 4.6 Copiar el Spreadsheet ID

De la URL del Spreadsheet:
```
https://docs.google.com/spreadsheets/d/1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms/edit
                                        └──────────────── SPREADSHEET_ID ──────────────────┘
```

Copiar el ID: `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms`

---

## Paso 5: Importar y Configurar Workflows

### 5.1 Importar workflows

1. En n8n, ir a **Workflows** en el menú lateral
2. Para cada archivo en la carpeta `workflows/` del repositorio:
   - Click en **"Add Workflow"** → **"Import from file"**
   - Seleccionar el archivo JSON
   - El workflow se importará con todos los nodos pre-configurados

Orden recomendado de importación:
1. `WF_MAIN_ROUTER.json`
2. `WF_FLOW_MENU.json`
3. `WF_FLOW_CARRITO.json`
4. `WF_FLOW_PEDIDO.json`
5. `WF_FLOW_ESTADO.json`
6. `WF_ADMIN_PANEL.json`
7. `WF_ADMIN_REPORTES.json`
8. `WF_SESSION_CLEANUP.json`

### 5.2 Configurar el Spreadsheet ID

En **cada workflow**, buscar los nodos de Google Sheets y reemplazar:

```
YOUR_SPREADSHEET_ID_HERE → (tu Spreadsheet ID real)
```

> **Tip**: Usar "Find & Replace" (Ctrl+H) si n8n lo soporta, o editar cada nodo individualmente.

### 5.3 Configurar variables de entorno

En cada workflow, buscar el nodo **"Config"** (generalmente el primer nodo Function) y actualizar:

```javascript
const CONFIG = {
  SPREADSHEET_ID: 'TU_SPREADSHEET_ID_AQUI',         // ← Cambiar
  ADMIN_CHAT_ID: '-100TU_CHAT_ID_ADMIN',             // ← Cambiar
  COCINA_GROUP_ID: '-100TU_CHAT_ID_COCINA',          // ← Cambiar
  TAX_RATE: 0.08,                                     // ← Ajustar si necesario
  SESSION_TTL_MIN: 30,                                 // ← Ajustar si necesario
  BOT_NAME: 'DeliveryBot',                            // ← Personalizar
  MAX_QTY_PER_ITEM: 5,
  MAX_CART_ITEMS: 10,
  ORDER_ID_PREFIX: 'ORD'
};
```

---

## Paso 6: Configurar Credenciales en n8n

### 6.1 Credencial de Telegram Bot API

1. En n8n, ir a **Settings** → **Credentials** (o desde el ícono de credenciales en la barra lateral)
2. Click en **"Add Credential"**
3. Buscar y seleccionar **"Telegram API"**
4. Configurar:
   - **Credential Name**: `DeliveryBot Telegram`
   - **Access Token**: Pegar el token del bot (ej: `7123456789:AAH1b...`)
5. Click en **"Save"**
6. Verificar con **"Test"** — debe mostrar la información del bot

### 6.2 Credencial de Google Sheets

1. En n8n, click en **"Add Credential"**
2. Buscar y seleccionar **"Google Sheets API"** (o "Google Sheets OAuth2 API")
3. Seleccionar tipo de autenticación: **"Service Account"**
4. Configurar:
   - **Credential Name**: `DeliveryBot Google Sheets`
   - **Service Account Email**: Pegar el `client_email` del archivo JSON
   - **Private Key**: Pegar el valor del campo `private_key` del archivo JSON
     - **Importante**: Incluir los marcadores `-----BEGIN PRIVATE KEY-----` y `-----END PRIVATE KEY-----`
5. Click en **"Save"**

### 6.3 Asignar credenciales a los nodos

En **cada workflow**:

1. Abrir el workflow en el editor
2. Para cada nodo de tipo **"Telegram"**:
   - Click en el nodo
   - En "Credential to connect with", seleccionar `DeliveryBot Telegram`
3. Para cada nodo de tipo **"Google Sheets"**:
   - Click en el nodo
   - En "Credential to connect with", seleccionar `DeliveryBot Google Sheets`
4. **Guardar** el workflow (Ctrl+S)

---

## Paso 7: Activar Workflows

### Orden de activación

Activar los workflows en este orden estricto para evitar problemas de dependencias:

| Orden | Workflow | Tipo de Trigger | Frecuencia |
|-------|----------|----------------|------------|
| 1️⃣ | `WF_SESSION_CLEANUP` | CRON | Cada 15 minutos |
| 2️⃣ | `WF_ADMIN_REPORTES` | CRON | Diario a las 23:55 |
| 3️⃣ | `WF_ADMIN_PANEL` | Webhook | Bajo demanda (callbacks) |
| 4️⃣ | `WF_FLOW_MENU` | Sub-workflow | Llamado por MAIN_ROUTER |
| 5️⃣ | `WF_FLOW_CARRITO` | Sub-workflow | Llamado por MAIN_ROUTER |
| 6️⃣ | `WF_FLOW_PEDIDO` | Sub-workflow | Llamado por MAIN_ROUTER |
| 7️⃣ | `WF_FLOW_ESTADO` | Sub-workflow | Llamado por MAIN_ROUTER |
| 8️⃣ | `WF_MAIN_ROUTER` | Webhook (Telegram) | **Activar último** |

### Cómo activar

Para cada workflow:
1. Abrir el workflow
2. En la esquina superior derecha, toggle el switch de **"Active"** a ON (verde)
3. Verificar que no hay errores de credenciales o configuración

> ⚠️ **Activar `WF_MAIN_ROUTER` último** porque al activarse, Telegram empezará a enviar mensajes. Si los sub-workflows no están activos, los mensajes fallarán.

---

## Paso 8: Testing y Verificación

### Checklist de Testing

Realizar estas pruebas en orden. Marcar cada una como completada:

#### Test 1: Conexión Básica
- [ ] Enviar `/start` al bot → Debe responder con menú principal
- [ ] Verificar que el mensaje tiene botones inline (🍽 Ver Menú, 🛒 Mi Carrito, 📦 Mis Pedidos)
- [ ] Verificar que se creó un registro en la hoja `USUARIOS`
- [ ] Verificar que se creó un registro en la hoja `SESSIONS` con `estado_fsm = IDLE`

#### Test 2: Navegación del Menú
- [ ] Click en "🍽 Ver Menú" → Debe mostrar categorías (Bebidas, Almuerzos, Snacks)
- [ ] Click en "Bebidas" → Debe mostrar lista de bebidas con precios
- [ ] Click en un producto → Debe mostrar selector de cantidad (1-5)
- [ ] Seleccionar cantidad → Debe confirmar "Agregado al carrito ✅"

#### Test 3: Carrito
- [ ] Click en "🛒 Mi Carrito" → Debe mostrar el producto recién agregado
- [ ] Verificar que muestra subtotal, impuesto y total correctamente
- [ ] Agregar un segundo producto → Debe aparecer en el carrito
- [ ] Eliminar un producto del carrito → Debe actualizarse el resumen
- [ ] Click en "Seguir comprando" → Debe volver a las categorías

#### Test 4: Pedido Completo
- [ ] Desde el carrito, click en "✅ Confirmar pedido"
- [ ] Debe mostrar resumen final con desglose
- [ ] Click en "✅ Sí, confirmar" → Debe generar ID de pedido
- [ ] Verificar mensaje de confirmación con ID (ej: ORD-20260604-0001)
- [ ] Verificar que el stock se decrementó en la hoja `MENU`
- [ ] Verificar que se creó un registro en `PEDIDOS`
- [ ] Verificar que se crearon registros en `DETALLE_LINEAS`

#### Test 5: Notificación a Cocina
- [ ] Verificar que el grupo de cocina recibió la notificación del pedido
- [ ] La notificación debe incluir botones para cambiar estado
- [ ] Click en "👨‍🍳 En Preparación" → Verificar que el usuario recibe notificación
- [ ] Click en "✅ Listo" → Verificar notificación al usuario
- [ ] Click en "🎉 Entregado" → Verificar notificación y `hora_entrega` en Sheets

#### Test 6: Estado de Pedidos
- [ ] Enviar `/estado` → Debe mostrar el pedido reciente con su estado actual
- [ ] Verificar la barra de progreso visual

#### Test 7: Comandos Globales
- [ ] Agregar productos al carrito, luego enviar `/cancelar` → Debe preguntar confirmación
- [ ] Enviar `/ayuda` → Debe mostrar instrucciones de uso
- [ ] Enviar `/start` en cualquier punto → Debe resetear y mostrar menú principal

#### Test 8: Edge Cases
- [ ] Intentar pedir más cantidad que el stock disponible → Debe rechazar
- [ ] Intentar confirmar un carrito vacío → Debe notificar que no hay productos
- [ ] Enviar texto libre en lugar de usar botones → Debe manejar gracefully
- [ ] Esperar más de 30 minutos sin interactuar → Verificar que la sesión se limpió

#### Test 9: Reportes (al día siguiente)
- [ ] Verificar que `WF_ADMIN_REPORTES` se ejecutó a las 23:55
- [ ] Verificar que se creó un registro en `REPORTES_CACHE`
- [ ] Verificar que el grupo de admin recibió el resumen diario

---

## Problemas Comunes y Soluciones

### Problema: El bot no responde a `/start`

**Causas posibles**:
1. El workflow `WF_MAIN_ROUTER` no está activo
2. El webhook no está configurado correctamente
3. El token de Telegram es incorrecto

**Solución**:
```bash
# Verificar el estado del webhook
curl "https://api.telegram.org/bot{TOKEN}/getWebhookInfo"
```

La respuesta debe mostrar:
- `url`: La URL de tu webhook n8n
- `has_custom_certificate`: false (si usas Let's Encrypt)
- `pending_update_count`: 0 (idealmente)
- `last_error_message`: (debe estar vacío)

Si el webhook no está configurado:
```bash
curl -X POST "https://api.telegram.org/bot{TOKEN}/setWebhook" \
  -d "url=https://tu-dominio.com/webhook/deliverybot" \
  -d "allowed_updates=[\"message\",\"callback_query\"]"
```

### Problema: Error "Credential not found" en n8n

**Solución**:
1. Ir a Settings → Credentials
2. Verificar que ambas credenciales existen (Telegram y Google Sheets)
3. Abrir cada workflow y re-seleccionar las credenciales en cada nodo
4. Guardar el workflow

### Problema: Error 403 en Google Sheets

**Causas posibles**:
1. El spreadsheet no está compartido con la cuenta de servicio
2. La API de Google Sheets no está habilitada

**Solución**:
1. Verificar que el spreadsheet está compartido con el email de la service account como **Editor**
2. En Google Cloud Console, verificar que Google Sheets API y Google Drive API están habilitadas
3. Verificar que la clave privada en las credenciales de n8n es correcta (incluyendo los markers BEGIN/END)

### Problema: Error 409 (Conflict) de Telegram

**Causa**: Hay dos procesos intentando recibir mensajes con el mismo token (por ejemplo, polling y webhook simultáneos, o dos instancias de n8n).

**Solución**:
```bash
# Eliminar el webhook existente
curl "https://api.telegram.org/bot{TOKEN}/deleteWebhook?drop_pending_updates=true"

# Re-configurar webhook
curl -X POST "https://api.telegram.org/bot{TOKEN}/setWebhook" \
  -d "url=https://tu-dominio.com/webhook/deliverybot"
```

### Problema: Pedidos no aparecen en Google Sheets

**Causas posibles**:
1. El Spreadsheet ID es incorrecto en los nodos de configuración
2. Los nombres de las hojas no coinciden exactamente (mayúsculas/minúsculas)

**Solución**:
1. Verificar el `SPREADSHEET_ID` en cada nodo Config
2. Verificar que los nombres de las hojas son **exactamente**: `MENU`, `PEDIDOS`, `USUARIOS`, `SESSIONS`, `DETALLE_LINEAS`, `REPORTES_CACHE`, `ERROR_LOG`
3. No debe haber espacios adicionales en los nombres

### Problema: El bot responde muy lento (>5 segundos)

**Causas posibles**:
1. Demasiadas llamadas individuales a Google Sheets API
2. El servidor de n8n tiene pocos recursos

**Solución**:
1. Implementar batch reads (ver `docs/arquitectura.md`)
2. Implementar caché de menú en static data de n8n
3. Verificar que el servidor tiene al menos 1GB de RAM y 1 vCPU
4. Verificar la latencia hacia Google Sheets API desde el servidor

### Problema: WF_SESSION_CLEANUP no restaura stock

**Causas posibles**:
1. El workflow CRON no está activo
2. El campo `carrito_json` tiene formato incorrecto

**Solución**:
1. Verificar que `WF_SESSION_CLEANUP` está activo (toggle verde)
2. Verificar la ejecución manual: abrir el workflow y click en "Execute Workflow"
3. Revisar los logs de ejecución para errores
4. Verificar que `carrito_json` contiene JSON válido en las sesiones

### Problema: Los reportes diarios no se generan

**Causas posibles**:
1. `WF_ADMIN_REPORTES` no está activo
2. El CRON está configurado incorrectamente
3. No hay pedidos con estado `ENTREGADO` en el día

**Solución**:
1. Verificar que el workflow está activo
2. Verificar la expresión CRON: debe ser `55 23 * * *` (23:55 diario)
3. Ejecutar manualmente para verificar que funciona
4. Verificar que hay pedidos con estado `ENTREGADO` en la fecha actual

---

## Siguiente Paso

Con el sistema desplegado y verificado, consulta los siguientes documentos para entender los detalles técnicos:

- **[`docs/arquitectura.md`](arquitectura.md)** — Arquitectura detallada, optimizaciones de API, y concurrencia
- **[`docs/fsm-estados.md`](fsm-estados.md)** — Máquina de estados, transiciones, y recuperación de errores
- **[`README.md`](../README.md)** — Referencia general del proyecto

---

*Documento actualizado: 2026-06-04*
