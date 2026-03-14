import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Flask, request, render_template, redirect, url_for, session, make_response
from core_shared import (
    obtener_conexion,
    inicializar_base_datos,
    verificar_jwt,
    generar_jwt,
    FLAG_SQL_INJECTION,
    FLAG_JWT,
)


app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta_123"

# Initialize database once at import time (replacing before_first_request hook)
inicializar_base_datos()


@app.route("/")
def index():
    """
    IntraCorp Employee Portal landing page.
    Shows login form, company news and employee directory.
    """
    return render_template("portal_home.html")


@app.route("/login", methods=["POST"])
def login():
    """
    LOGIN ENDPOINT - VULNERABLE TO SQL INJECTION

    IMPORTANT: This preserves the original vulnerable logic from the
    monolithic application. Only surrounding routing / templates changed.
    """
    mensaje_error = None

    usuario = request.form.get("usuario", "")
    password = request.form.get("password", "")

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # VULNERABILIDAD: SQL Injection - Concatenación directa de entrada del usuario
    consulta = f"SELECT * FROM usuarios WHERE usuario='{usuario}' AND password='{password}'"
    print(f"[DEBUG] Consulta SQL: {consulta}")

    try:
        cursor.execute(consulta)
        usuario_encontrado = cursor.fetchone()

        if usuario_encontrado:
            session["usuario_id"] = usuario_encontrado["id"]
            session["usuario"] = usuario_encontrado["usuario"]
            session["rol"] = usuario_encontrado["rol"]

            # Generar JWT vulnerable
            token = generar_jwt(
                {
                    "usuario_id": usuario_encontrado["id"],
                    "usuario": usuario_encontrado["usuario"],
                    "rol": usuario_encontrado["rol"],
                }
            )

            respuesta = make_response(redirect(url_for("panel")))
            respuesta.set_cookie("token_jwt", token)

            # Solo marcar la flag de SQLi cuando el inicio de sesión
            # se logra gracias a la inyección y no con credenciales válidas normales.
            cursor.execute(
                "SELECT * FROM usuarios WHERE usuario = ? AND password = ?",
                (usuario, password),
            )
            usuario_legitimo = cursor.fetchone()
            if not usuario_legitimo:
                session["flag_sql"] = FLAG_SQL_INJECTION
            else:
                session.pop("flag_sql", None)

            conexion.close()
            return respuesta
        else:
            mensaje_error = "Credenciales incorrectas"
    except Exception as e:
        mensaje_error = f"Error en la consulta: {str(e)}"

    conexion.close()

    return render_template("portal_home.html", mensaje_error=mensaje_error)


@app.route("/panel")
def panel():
    """Dashboard for logged-in users, with JWT vulnerability preserved."""
    if "usuario" not in session:
        return redirect(url_for("index"))

    token = request.cookies.get("token_jwt")
    datos_jwt = None
    flag_jwt = None

    if token:
        datos_jwt = verificar_jwt(token)
        # Si el usuario modificó el token para ser admin
        if datos_jwt and datos_jwt.get("rol") == "admin" and session.get("rol") != "admin":
            flag_jwt = FLAG_JWT

    return render_template(
        "panel.html",
        usuario=session.get("usuario"),
        rol=session.get("rol"),
        flag_sql=session.get("flag_sql"),
        flag_jwt=flag_jwt,
        datos_jwt=datos_jwt,
    )


@app.route("/logout")
def logout():
    """Cierra la sesión del usuario."""
    session.clear()
    respuesta = make_response(redirect(url_for("index")))
    respuesta.delete_cookie("token_jwt")
    return respuesta


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

