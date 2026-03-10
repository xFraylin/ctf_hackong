# ACME Hack ERP - Edición HackConRD
# Aplicación deliberadamente vulnerable para laboratorio CTF
# NO USAR EN PRODUCCIÓN - Solo para fines educativos

from flask import Flask, request, render_template, render_template_string, redirect, url_for, session, send_file, make_response, jsonify
import sqlite3
import jwt
import os
import threading
import time
from functools import wraps

app = Flask(__name__)
app.secret_key = 'clave_super_secreta_123'  # Secreto hardcodeado vulnerable

# Secreto JWT hardcodeado (vulnerable)
JWT_SECRET = 'secreto_jwt_debil'

# Ruta de la base de datos en /tmp (directorio con permisos de escritura)
DATABASE_PATH = '/tmp/base_datos.db'

# Flags del CTF (prefijo HackCon + nombre de la vulnerabilidad)
FLAG_SQL_INJECTION = 'flag{hackcon_sql_injection}'
FLAG_IDOR = 'flag{hackcon_idor}'
FLAG_LFI = 'flag{hackcon_lfi}'
FLAG_XSS = 'flag{hackcon_xss}'
FLAG_SSTI = 'flag{hackcon_command_injection}'
FLAG_JWT = 'flag{hackcon_jwt}'

def obtener_conexion():
    """Obtiene conexión a la base de datos SQLite"""
    conexion = sqlite3.connect(DATABASE_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion

def inicializar_base_datos():
    """Inicializa la base de datos con datos de ejemplo"""
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # Crear tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            password TEXT NOT NULL,
            rol TEXT DEFAULT 'empleado',
            flag TEXT
        )
    ''')
    
    # Crear tabla de facturas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS facturas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            cliente TEXT,
            monto REAL,
            descripcion TEXT,
            flag TEXT
        )
    ''')
    
    # Crear tabla de tickets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            asunto TEXT,
            mensaje TEXT,
            fecha TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Verificar si ya existen usuarios
    cursor.execute('SELECT COUNT(*) FROM usuarios')
    if cursor.fetchone()[0] == 0:
        # Insertar usuarios de ejemplo
        cursor.execute("INSERT INTO usuarios (usuario, password, rol, flag) VALUES ('admin', 'admin123', 'admin', ?)", (FLAG_JWT,))
        cursor.execute("INSERT INTO usuarios (usuario, password, rol) VALUES ('empleado', 'empleado123', 'empleado')")
        
        # Insertar facturas normales (visibles en el dashboard)
        cursor.execute("INSERT INTO facturas (usuario_id, cliente, monto, descripcion) VALUES (2, 'Cliente ABC', 1500.00, 'Servicios de consultoria')")
        cursor.execute("INSERT INTO facturas (usuario_id, cliente, monto, descripcion) VALUES (2, 'Cliente XYZ', 2300.50, 'Desarrollo de software')")
        cursor.execute("INSERT INTO facturas (usuario_id, cliente, monto, descripcion) VALUES (2, 'Empresa Delta', 4200.00, 'Mantenimiento anual')")
        cursor.execute("INSERT INTO facturas (usuario_id, cliente, monto, descripcion) VALUES (2, 'Corp Solutions', 1850.75, 'Licencias de software')")
        cursor.execute("INSERT INTO facturas (usuario_id, cliente, monto, descripcion) VALUES (2, 'Tech Partners', 3100.00, 'Integracion de sistemas')")
        
        # Factura secreta con ID alto (101) - solo accesible via IDOR
        cursor.execute("INSERT INTO facturas (id, usuario_id, cliente, monto, descripcion, flag) VALUES (101, 1, 'Cliente Interno', 999999.99, 'Factura confidencial - Auditoria interna', ?)", (FLAG_IDOR,))
        
        # Insertar ticket de ejemplo con flag XSS
        cursor.execute("INSERT INTO tickets (usuario_id, asunto, mensaje) VALUES (1, 'Bienvenida', ?)", (f'Bienvenido al sistema. Flag oculta: {FLAG_XSS}',))
    
    conexion.commit()
    conexion.close()

def verificar_jwt(token):
    """Verificación JWT vulnerable - acepta alg=none o HS256 con secreto débil"""
    try:
        # Intentar decodificación normal con HS256 y secreto débil
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except Exception:
        # Si falla, aceptar tokens forjados con alg=none sin verificar firma
        try:
            partes = token.split('.')
            if len(partes) == 3:
                import base64
                import json

                header_padding = partes[0] + '=' * (4 - len(partes[0]) % 4)
                header = json.loads(base64.urlsafe_b64decode(header_padding))

                if header.get('alg', '').lower() == 'none':
                    payload_padding = partes[1] + '=' * (4 - len(partes[1]) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(payload_padding))
                    return payload
        except Exception as e:
            print(f"Error JWT (alg=none): {e}")
        return None

def generar_jwt(datos):
    """Genera token JWT con secreto débil"""
    return jwt.encode(datos, JWT_SECRET, algorithm='HS256')

@app.route('/')
def inicio():
    """Página de inicio - redirige al login"""
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Página de login - VULNERABLE A SQL INJECTION
    La consulta se construye concatenando directamente los datos del usuario
    """
    mensaje_error = None
    
    if request.method == 'POST':
        usuario = request.form.get('usuario', '')
        password = request.form.get('password', '')
        
        conexion = obtener_conexion()
        cursor = conexion.cursor()
        
        # VULNERABILIDAD: SQL Injection - Concatenación directa de entrada del usuario
        consulta = f"SELECT * FROM usuarios WHERE usuario='{usuario}' AND password='{password}'"
        print(f"[DEBUG] Consulta SQL: {consulta}")
        
        try:
            cursor.execute(consulta)
            usuario_encontrado = cursor.fetchone()
            
            if usuario_encontrado:
                session['usuario_id'] = usuario_encontrado['id']
                session['usuario'] = usuario_encontrado['usuario']
                session['rol'] = usuario_encontrado['rol']
                
                # Generar JWT vulnerable
                token = generar_jwt({
                    'usuario_id': usuario_encontrado['id'],
                    'usuario': usuario_encontrado['usuario'],
                    'rol': usuario_encontrado['rol']
                })
                
                respuesta = make_response(redirect(url_for('panel')))
                respuesta.set_cookie('token_jwt', token)
                
                # Solo marcar la flag de SQLi cuando el inicio de sesión
                # se logra gracias a la inyección y no con credenciales válidas normales.
                cursor.execute(
                    "SELECT * FROM usuarios WHERE usuario = ? AND password = ?",
                    (usuario, password)
                )
                usuario_legitimo = cursor.fetchone()
                if not usuario_legitimo:
                    session['flag_sql'] = FLAG_SQL_INJECTION
                else:
                    session.pop('flag_sql', None)
                
                conexion.close()
                return respuesta
            else:
                mensaje_error = 'Credenciales incorrectas'
        except Exception as e:
            mensaje_error = f'Error en la consulta: {str(e)}'
        
        conexion.close()
    
    return render_template('login.html', mensaje_error=mensaje_error)

@app.route('/panel')
def panel():
    """Panel principal del sistema"""
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    # Verificar token JWT si existe
    token = request.cookies.get('token_jwt')
    datos_jwt = None
    flag_jwt = None
    
    if token:
        datos_jwt = verificar_jwt(token)
        # Si el usuario modificó el token para ser admin
        if datos_jwt and datos_jwt.get('rol') == 'admin' and session.get('rol') != 'admin':
            flag_jwt = FLAG_JWT
    
    return render_template('panel.html', 
                         usuario=session.get('usuario'),
                         rol=session.get('rol'),
                         flag_sql=session.get('flag_sql'),
                         flag_jwt=flag_jwt,
                         datos_jwt=datos_jwt)

@app.route('/factura')
def factura():
    """
    Visor de facturas - VULNERABLE A IDOR
    No verifica que la factura pertenezca al usuario actual
    """
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    factura_id = request.args.get('id', 1)
    
    conexion = obtener_conexion()
    cursor = conexion.cursor()
    
    # VULNERABILIDAD: IDOR - No verifica permisos del usuario
    cursor.execute(f"SELECT * FROM facturas WHERE id = {factura_id}")
    factura_data = cursor.fetchone()
    conexion.close()
    
    return render_template('factura.html', 
                         factura=factura_data,
                         usuario=session.get('usuario'))

@app.route('/ticket', methods=['GET', 'POST'])
def ticket():
    """
    Sistema de tickets - VULNERABLE A XSS ALMACENADO
    Los mensajes se guardan y muestran sin sanitización
    """
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    mensaje_exito = None
    
    # Los tickets ahora se almacenan solo en la sesión del usuario actual
    if 'tickets' not in session:
        session['tickets'] = []
    
    if request.method == 'POST':
        asunto = request.form.get('asunto', '')
        mensaje = request.form.get('mensaje', '')
        
        # VULNERABILIDAD: XSS Almacenado - No sanitiza la entrada
        tickets = session['tickets']
        nuevo_id = tickets[-1]['id'] + 1 if tickets else 1
        tickets.append({
            'id': nuevo_id,
            'usuario_id': session.get('usuario_id'),
            'asunto': asunto,
            'mensaje': mensaje,
            'fecha': time.strftime('%Y-%m-%d %H:%M:%S'),
        })
        session['tickets'] = tickets
        
        mensaje_exito = 'Ticket creado exitosamente.'
    
    tickets = session.get('tickets', [])
    
    return render_template(
        'ticket.html',
        tickets=tickets,
        mensaje_exito=mensaje_exito,
        usuario=session.get('usuario'),
        rol=session.get('rol'),
    )

@app.route('/ticket/<int:ticket_id>')
def ver_ticket(ticket_id):
    """
    Ver detalle de un ticket individual - Aqui se ejecuta el XSS
    Solo el admin deberia ver los mensajes completos
    """
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    tickets = session.get('tickets', [])
    ticket_data = next((t for t in tickets if t['id'] == ticket_id), None)
    
    if not ticket_data:
        return "Ticket no encontrado", 404
    
    return render_template(
        'ticket_detalle.html',
        ticket=ticket_data,
        usuario=session.get('usuario'),
        rol=session.get('rol'),
    )

@app.route('/perfil', methods=['GET'])
def perfil():
    """
    Herramienta de diagnóstico de red con ping
    (VULNERABLE A COMMAND INJECTION en el parámetro 'host')
    """
    if 'usuario' not in session:
        return redirect(url_for('login'))

    host = request.args.get('host', '').strip()
    resultado = None

    if host:
        # Bloqueo básico de comandos específicos
        if "cat" in host.lower():
            resultado = "Comando no permitido"
        else:
            comando = f"ping -c 1 {host}"
            resultado = os.popen(comando).read()

    return render_template(
        'perfil.html',
        usuario=session.get('usuario'),
        rol=session.get('rol'),
        host=host,
        resultado=resultado,
    )

@app.route('/descargar')
def descargar():
    """
    Descarga de archivos - VULNERABLE A LFI
    Abre archivos usando directamente el parámetro del usuario
    """
    if 'usuario' not in session:
        return redirect(url_for('login'))
    
    archivo = request.args.get('archivo')
    
    # Si no se especifica archivo, mostrar lista de documentos disponibles
    if not archivo:
        try:
            archivos = []
            for nombre in os.listdir('uploads'):
                ruta = os.path.join('uploads', nombre)
                if os.path.isfile(ruta):
                    archivos.append(nombre)
            
            archivos.sort()
            items = ''.join(
                f'<li><a href="/descargar?archivo={nombre}">{nombre}</a></li>'
                for nombre in archivos
            )
            
            return f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>ACME Documentos - Descargas</title>
</head>
<body>
    <h2>Archivos disponibles</h2>
    <ul>
        {items}
    </ul>
</body>
</html>
"""
        except Exception as e:
            return f'Error al listar archivos: {str(e)}'
    
    # VULNERABILIDAD: LFI - Local File Inclusion
    # No valida ni sanitiza la ruta del archivo
    ruta_archivo = "uploads/" + archivo
    
    try:
        # Intenta leer el archivo
        with open(ruta_archivo, 'r') as f:
            contenido = f.read()
        return f'<pre>{contenido}</pre>'
    except Exception as e:
        return f'Error al leer archivo: {str(e)}'

@app.route('/logout')
def logout():
    """Cierra la sesión del usuario"""
    session.clear()
    respuesta = make_response(redirect(url_for('login')))
    respuesta.delete_cookie('token_jwt')
    return respuesta

if __name__ == '__main__':
    # Crear directorios necesarios
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    # Crear documentos corporativos de ejemplo en uploads
    documentos = {
        'manual_usuario.txt': (
            "ACME Corporation - Manual de Usuario\n"
            "Guía básica de uso del sistema ERP ACME.\n"
            "Incluye procedimientos generales para usuarios finales."
        ),
        'politica_seguridad.txt': (
            "ACME Corporation - Política de Seguridad de la Información\n"
            "Este documento describe las políticas internas de seguridad,\n"
            "controles de acceso y manejo de información sensible."
        ),
        'contrato_cliente.txt': (
            "ACME Corporation - Contrato Estándar para Clientes\n"
            "Términos y condiciones del servicio de plataforma ERP."
        ),
        'procedimiento_backup.txt': (
            "ACME Corporation - Procedimiento de Respaldo de Base de Datos\n"
            "Frecuencia de respaldos, almacenamiento y pruebas de restauración."
        ),
        'reporte_financiero.txt': (
            "ACME Corporation - Reporte Financiero Trimestral\n"
            "Resumen ejecutivo de ingresos, gastos y proyecciones."
        ),
    }
    for nombre, contenido in documentos.items():
        ruta = os.path.join('uploads', nombre)
        if not os.path.exists(ruta):
            with open(ruta, 'w') as f:
                f.write(contenido)
    
    # Inicializar base de datos
    inicializar_base_datos()
    
    # Ejecutar aplicación
    print("=" * 50)
    print("ACME Hack ERP - Edición HackConRD")
    print("Laboratorio CTF de Ciberseguridad")
    print("=" * 50)
    print("\nVulnerabilidades disponibles:")
    print("1. SQL Injection en /login")
    print("2. IDOR en /factura?id=")
    print("3. LFI en /descargar?archivo=")
    print("4. XSS Almacenado en /ticket")
    print("5. SSTI en /perfil?nombre=")
    print("6. JWT Inseguro en cookies")
    print("\n" + "=" * 50)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
