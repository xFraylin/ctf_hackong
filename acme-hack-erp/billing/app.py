import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Flask, render_template, request, redirect, url_for, session
from core_shared import obtener_conexion, inicializar_base_datos


app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta_123"

# Initialize database once at import time (replacing before_first_request hook)
inicializar_base_datos()


@app.route("/")
def index():
    """
    IntraCorp Billing Dashboard landing page.
    Shows invoice table and Generate Invoice form.
    """
    clientes = ["Delta Corp", "Omega Ltd", "TechWorks", "Nova Systems"]
    return render_template("billing_home.html", clientes=clientes)


@app.route("/factura")
def factura():
    """
    Visor de facturas - VULNERABLE A IDOR
    No verifica que la factura pertenezca al usuario actual.
    """
    if "usuario" not in session:
        # Requiere sesión compartida con el portal (mismo SECRET_KEY).
        return redirect("http://localhost:8091")

    factura_id = request.args.get("id", 1)

    conexion = obtener_conexion()
    cursor = conexion.cursor()

    # VULNERABILIDAD: IDOR - No verifica permisos del usuario
    cursor.execute(f"SELECT * FROM facturas WHERE id = {factura_id}")
    factura_data = cursor.fetchone()
    conexion.close()

    return render_template(
        "factura.html",
        factura=factura_data,
        usuario=session.get("usuario"),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

