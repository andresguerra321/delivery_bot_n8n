# 🚀 Tutorial de Instalación y Pruebas: DeliveryBot

Este tutorial te guiará paso a paso para desplegar todo el sistema en tu entorno local o en la nube, y realizar tu primera prueba end-to-end (de extremo a extremo).

---

## 🛠️ Fase 1: Configurar la Base de Datos (Google Sheets)

Google Sheets actuará como el cerebro de almacenamiento de nuestro bot.

1. Ve a [Google Sheets](https://sheets.google.com) y crea una nueva hoja de cálculo en blanco. Nómbrala **DeliveryBot_DB**.
2. Cambia el nombre de la primera pestaña a `MENU`.
3. Crea **6 pestañas adicionales** y nómbralas exactamente así (en mayúsculas):
   - `PEDIDOS`
   - `USUARIOS`
   - `SESSIONS`
   - `DETALLE_LINEAS`
   - `REPORTES_CACHE`
   - `ERROR_LOG`
4. Abre la carpeta `sheets/` que se generó en tus archivos locales. Verás varios archivos `.csv`.
5. En Google Sheets, ve a **Archivo > Importar > Subir** y selecciona `MENU_sample.csv`.
   - En ubicación de importación, selecciona **Reemplazar la hoja actual** (asegúrate de estar en la pestaña MENU).
   - Repite este proceso para el resto de pestañas usando su archivo `_template.csv` correspondiente.
6. Copia el **Spreadsheet ID**. Lo encontrarás en la URL de tu hoja de cálculo, es la cadena larga de letras y números.
   - Ejemplo: `https://docs.google.com/spreadsheets/d/`**`1BxiMVs0XRYFgCEKU_18m1...`**`/edit`
7. (Opcional pero recomendado) Si usarás credenciales OAuth2 de Google Cloud, asegúrate de habilitar la **Google Sheets API** en tu Google Cloud Console.

---

## 🤖 Fase 2: Crear el Bot de Telegram

1. Abre Telegram y busca al usuario **@BotFather** (el oficial con un check azul).
2. Envía el comando `/newbot`.
3. Sigue las instrucciones:
   - Nombre: `MiCafeteriaBot` (o el que prefieras).
   - Username: `MiCafeteria_Delivery_Bot` (debe terminar en bot).
4. BotFather te dará un **Token de Acceso** HTTP API (algo como `123456789:ABCdefGHIjkl...`). **Guárdalo en un lugar seguro**, lo usaremos pronto.
5. Envía a BotFather el comando `/setcommands`, selecciona tu bot, y pega lo siguiente para crear el menú del sistema:
   
   ```text
   start - 🔄 Iniciar o reiniciar el bot
   cancelar - ❌ Cancelar pedido en curso
   estado - 📍 Ver en qué va mi pedido
   ```

---

## ⚙️ Fase 3: Desplegar en n8n

### 3.1. Importar los flujos (Workflows)

1. Abre tu instancia de **n8n** (ya sea Desktop, Docker o Cloud).
2. Ve a la pestaña **Workflows** y haz clic en **Add Workflow**.
3. En la esquina superior derecha del lienzo, haz clic en el botón de opciones (tres puntos) y selecciona **Import from File**.
4. Importa todos los archivos `.json` que están en la carpeta `workflows/` de tu proyecto.
   
   > **Nota:** Importa primero los de nombre `WF_FLOW_...`, luego los `WF_ADMIN_...` y de último `WF_MAIN_ROUTER`.

### 3.2. Configurar Credenciales

Debes configurar las credenciales en n8n para que pueda hablar con Telegram y Google Sheets:

1. Ve a **Credentials** en el menú izquierdo de n8n.
2. Añade nueva credencial para **Telegram API**:
   - Pega el **Token** que te dio BotFather.
   - Guárdala con el nombre `telegramApi`.
3. Añade nueva credencial para **Google Sheets**:
   - Usa OAuth2 (recomendado para cuentas personales) o Service Account.
   - Completa el login con la cuenta de Google donde creaste la base de datos.
   - Guárdala con el nombre `googleSheetsOAuth2Api`.

### 3.3. Configurar Nodos en el `WF_MAIN_ROUTER`

1. Abre el workflow **WF_MAIN_ROUTER**.
2. Abre el nodo de Telegram Trigger y asegúrate de que tiene seleccionada la credencial de Telegram que acabas de crear.
3. Abre el nodo de Google Sheets y asegúrate de:
   - Seleccionar tu credencial.
   - En `Document ID`, pegar el **Spreadsheet ID** que copiaste en la Fase 1.
4. Repite el paso del Spreadsheet ID en los workflows secundarios que lean/escriban en Sheets (`WF_FLOW_PEDIDO`, `WF_ADMIN_REPORTES`, etc.).
5. **Activa (Toggle ON)** todos tus workflows. n8n conectará automáticamente el Webhook de Telegram.

---

## 🧪 Fase 4: Primera Prueba (End-to-End Test)

¡Hora de la verdad! Vamos a hacer un pedido real.

### Paso 1: Interactuar con el Bot

1. Ve a Telegram, busca tu bot y presiona **Iniciar** (o escribe `/start`).
2. El bot debe leer tu mensaje, registrar tu `telegram_id` en la hoja `SESSIONS` y enviarte el **Menú Principal**.
3. Presiona el botón de **🛒 Hacer Pedido**.

### Paso 2: Flujo de Compra

1. El bot te mostrará las categorías (Bebidas, Almuerzos, Snacks). Elige una.
2. Selecciona un producto (ej. "Café Americano").
3. Elige la cantidad (ej. "2").
4. El bot te mostrará el carrito parcial. Haz clic en **✅ Confirmar Pedido**.

### Paso 3: Validación Técnica

1. Abre tu hoja de Google Sheets.
2. En la pestaña `PEDIDOS`, debería haber aparecido una fila nueva con tu orden, estado `RECIBIDO` y tu total calculado.
3. En la pestaña `DETALLE_LINEAS`, deberías ver los productos desglosados de tu orden.
4. En la pestaña `MENU`, revisa el stock del "Café Americano". **¡Debería haber bajado automáticamente en 2 unidades!** Esto significa que el *Optimistic Locking* funcionó.

### Paso 4: Flujo de Cocina (Admin)

1. Para probar la cocina, ve al workflow `WF_ADMIN_PANEL`.
2. Asumiendo que simulaste un callback de admin (o forzaste el trigger), el estado en la pestaña `PEDIDOS` debería cambiar de `RECIBIDO` a `PREPARACION`.
3. Automáticamente, te llegará un mensaje a tu Telegram diciendo *"👨‍🍳 Tu pedido está siendo preparado..."*.

---

## 🎉 ¡Felicidades!

Tu sistema DeliveryBot está completamente operativo. Si en algún momento la lógica se traba, recuerda que tienes el comando `/start` como botón de pánico para reiniciar la sesión, y el `WF_SESSION_CLEANUP` corriendo cada 15 minutos en n8n para mantener tu base de datos limpia de carritos abandonados.
