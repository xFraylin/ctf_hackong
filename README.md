## ACME Hack ERP – CTF HackonG

**ACME Hack ERP** es una aplicación web deliberadamente vulnerable, pensada como laboratorio para un CTF de ciberseguridad (solo fines educativos, **no usar en producción**). Simula un pequeño ERP (panel, facturas, tickets, descargas, perfil de red) construido con Flask y SQLite dentro de un contenedor Docker.

Este proyecto agrupa varias vulnerabilidades web clásicas para que los participantes practiquen explotación, obtención de flags y análisis de código.

---

### 🧩 Vulnerabilidades incluidas

- **SQL Injection (SQLi) – `/login`**
- **IDOR (Insecure Direct Object Reference) – `/factura?id=`**
- **LFI (Local File Inclusion / Path Traversal) – `/descargar?archivo=`**
- **XSS almacenado – `/ticket` y `/ticket/&lt;id&gt;`**
- **Command Injection – `/perfil?host=`**
- **JWT inseguro (alg=none / secreto débil) – cookie `token_jwt`**

Cada vulnerabilidad tiene asociada una flag tipo `flag{...}` que se mostrará al explotarla correctamente.

---

### 🚀 Puesta en marcha rápida

```bash
cd acme-hack-erp
docker compose up --build
```

Después de que el contenedor esté arriba, accede a:

- `http://localhost:5000` → aplicación principal.

Credenciales de ejemplo (usuarios “legítimos”):

- Usuario: `empleado` – Contraseña: `empleado123`
- Usuario: `admin` – Contraseña: `admin123`

> Para un entorno de CTF, se recomienda levantar **una instancia por equipo** (por ejemplo, con distintos puertos/`docker compose -p equipoX ...`) para que no compartan flags ni estado.

---

### 1️⃣ SQL Injection – `/login`

- **Qué es**: Construcción de la consulta SQL concatenando directamente los datos del formulario, sin usar parámetros preparados.
- **Código relevante**: en `app.py`, función `login()`:
  - `consulta = f"SELECT * FROM usuarios WHERE usuario='{usuario}' AND password='{password}'"`
- **Objetivo**: iniciar sesión sin conocer la contraseña real y activar la flag `flag{hackcon_sql_injection}` que se muestra en el panel.

**Cómo explotarla (idea básica)**

1. Ir a `/login`.
2. En el campo **usuario** introducir algo como:
   - `admin'--`  
   y en contraseña cualquier valor.
3. También puedes usar un payload estilo:
   - Usuario: `' OR 1=1--`  
   - Contraseña: lo que sea.
4. Si el `SELECT` devuelve un usuario gracias a la inyección (y no por credenciales válidas), la app marcará la flag de SQLi y al entrar al panel `/panel` verás la tarjeta:
   - `🏆 ¡Flag Capturada! - SQL Injection` con `flag{sql_injection_master}`.

---

### 2️⃣ IDOR – `/factura?id=`

- **Qué es**: Insecure Direct Object Reference. La app permite acceder a recursos (facturas) solo por ID, sin verificar que pertenezcan al usuario autenticado.
- **Código relevante**: en `app.py`, función `factura()`:
  - `cursor.execute(f"SELECT * FROM facturas WHERE id = {factura_id}")`
- **Objetivo**: acceder a la factura secreta con ID alto y obtener `flag{hackcon_idor}`.

**Cómo explotarla (idea básica)**

1. Iniciar sesión como `empleado`.
2. Visitar `/factura?id=1`, `/factura?id=2`, etc., para ver facturas normales.
3. Probar un ID “raro” más alto; en este lab la factura especial se inserta con un ID grande (por ejemplo `101`):
   - Ir a `http://localhost:5000/factura?id=101`.
4. Si existe y no es del usuario, verás una tarjeta de flag en la parte inferior de la página de factura con:
   - `🏆 ¡Flag Capturada! - IDOR` y `flag{idor_access_granted}`.

---

### 3️⃣ LFI / Path Traversal – `/descargar?archivo=`

- **Qué es**: La ruta lee directamente el archivo indicado por el parámetro `archivo`, sin sanitizar el path. Permite recorrer directorios y leer archivos arbitrarios del contenedor.
- **Código relevante**: en `app.py`, función `descargar()`:
  - `ruta_archivo = "uploads/" + archivo`
  - `with open(ruta_archivo, 'r') as f: contenido = f.read()`
- **Objetivo**: abusar de la LFI/Path Traversal para llegar al archivo de flag `flag_lfi.txt` y así obtener `flag{hackcon_lfi}`.

**Cómo explotarla (idea básica)**

1. Ir a `/descargar` (sin parámetros) para ver la lista de archivos legítimos en `uploads/`.
2. Probar rutas con `../` para salir de la carpeta `uploads`. Ejemplos típicos:
   - `/descargar?archivo=../flag_lfi.txt`
   - o, según dónde se haya montado el volumen, variantes con más `../`.
3. Cuando aciertes el path correcto, el contenido del archivo se mostrará en `<pre>`, incluyendo la flag `flag{lfi_root_access}`.

> Nota: el path exacto puede cambiar según cómo montes el contenedor; juega con `../` hasta alcanzar la raíz del proyecto dentro del contenedor.

---

### 4️⃣ XSS almacenado – `/ticket` y `/ticket/<id>`

- **Qué es**: Cross-Site Scripting almacenado. La app guarda el mensaje del ticket sin sanitizarlo y luego lo renderiza con `|safe`, permitiendo ejecutar JavaScript cuando alguien (por ejemplo un administrador/bot) ve el detalle del ticket.
- **Código relevante**:
  - En `app.py`, función `ticket()` almacena `mensaje` tal cual en la sesión.
  - En `templates/ticket_detalle.html` se renderiza: `{{ ticket.mensaje | safe }}`.
- **Objetivo**: crear un ticket cuyo mensaje ejecute JS y dispare la flag `flag{hackcon_xss}`.

**Cómo explotarla (idea básica)**

1. Iniciar sesión.
2. Ir a `/ticket`.
3. Crear un nuevo ticket con un payload en el campo **Mensaje**, por ejemplo:

   ```html
   <script>alert('XSS');</script>
   ```

4. Al ver el detalle del ticket (`/ticket/<id>`), el navegador ejecutará el script. El HTML y el JS del lab también pueden simular un “bot admin” y mostrar/registrar la flag cuando detectan `<script>` en el contenido.
5. La flag asociada es `flag{stored_xss_triggered}`.

> Para un CTF real, puedes cambiar el payload recomendado y la forma de reportar la cookie/flag (por ejemplo, haciendo `fetch` hacia un endpoint tipo `/api/reportar-xss`).

---

### 5️⃣ Command Injection – `/perfil?host=`

- **Qué es**: la app construye un comando de sistema (`ping`) concatenando directamente el parámetro `host`. Un atacante puede inyectar otros comandos usando operadores del shell (`;`, `&&`, `|`, etc.).
- **Código relevante**: en `app.py`, función `perfil()`:
  - `comando = f"ping -c 1 {host}"`
  - `resultado = os.popen(comando).read()`
- **Objetivo**: ejecutar comandos arbitrarios dentro del contenedor y, en particular, leer archivos sensibles como `flag_ssti.txt` (o cualquier otro que definas para esta vuln), donde se encuentra `flag{hackcon_command_injection}`.

**Cómo explotarla (idea básica)**

1. Ir a `/perfil`.
2. En el campo **host**, en lugar de un dominio poner algo como:
   - `8.8.8.8; ls`
   - o `127.0.0.1; cat flag_ssti.txt`
3. El comando final que ejecuta el servidor será algo tipo:
   - `ping -c 1 127.0.0.1; cat flag_ssti.txt`
4. La salida combinada de `ping` + `cat` aparecerá en la página, exponiendo el contenido de `flag_ssti.txt` con la flag correspondiente.

> Hay un bloqueo muy básico que mira si el string `cat` está presente en minúsculas; puedes evadirlo con trucos (`/bin/cat`, `c''at`, etc.) si quieres hacerlo más interesante.

---

### 6️⃣ JWT inseguro – cookie `token_jwt`

- **Qué es**: el sistema de autenticación usa JWT con un secreto débil y además acepta tokens con `alg: none` sin verificar firma. Esto permite forjar tokens que te den rol de administrador.
- **Código relevante**:
  - `JWT_SECRET = 'secreto_jwt_debil'`
  - Función `verificar_jwt()` en `app.py` acepta `alg=none`.
  - En `panel()` se comprueba si el JWT dice que eres `admin` aunque la sesión no lo sea, y entonces muestra `flag{jwt_pwned}`.
- **Objetivo**: modificar/forjar el JWT para cambiar tu rol a `admin` y disparar la flag `flag{hackcon_jwt}`.

**Cómo explotarla (idea básica)**

1. Inicia sesión normal como `empleado` y captura la cookie `token_jwt` (con las herramientas de dev del navegador).
2. Decodifica el JWT (header y payload) usando cualquier herramienta online o script.
3. Crea un nuevo token con **algoritmo `none`** y payload modificado, por ejemplo:

   ```json
   {
     "usuario_id": 2,
     "usuario": "empleado",
     "rol": "admin"
   }
   ```

4. Monta el token con `alg: "none"` y **sin firma**, y reemplaza la cookie `token_jwt` del navegador por esta versión.
5. Refresca `/panel`; si el backend acepta el JWT sin firma y ve `rol: admin` en el payload mientras tu sesión normal no es admin, mostrará la tarjeta de flag de JWT inseguro con `flag{jwt_pwned}`.

> Alternativamente, también podrías firmar un JWT HS256 usando el secreto débil conocido (`secreto_jwt_debil`), lo que ilustra un ataque por fuerza bruta de secretos poco robustos.

---

### 🔐 Aviso importante

Este proyecto es **intencionalmente inseguro** y está diseñado solo para prácticas de CTF y aprendizaje de seguridad ofensiva en entornos controlados.  
No lo expongas directamente a internet ni reutilices este código en aplicaciones reales. Ajusta o cambia las flags antes de usarlo en eventos públicos.

