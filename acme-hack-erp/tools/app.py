import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Flask, request, render_template
from core_shared import inicializar_base_datos


app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta_123"

# Initialize database once at import time (replacing before_first_request hook)
inicializar_base_datos()


@app.route("/")
def index():
    """
    IntraCorp Network Diagnostics landing page.
    Lists available tools, with Ping Host wired to the vulnerable backend.
    """
    return render_template("tools_home.html")


@app.route("/ping", methods=["GET"])
def ping():
    """
    Herramienta de ping - VULNERABLE A COMMAND INJECTION en el parámetro 'host'.

    This preserves the original vulnerable logic from /perfil (seccion=ping).
    """
    host = request.args.get("host", "").strip()
    resultado = None

    if host:
        # Blacklist de comandos/operadores peligrosos (manteniendo la lógica vulnerable)
        host_lower = host.lower()
        tokens_prohibidos = [
            "cat",
            "less",
            "more",
            "tac",
            "nl",
            "awk",
            "sed",
            "cut",
            "strings",
            "&",
            "|",
            "||",
            "&&",
            "`",
            "$(",
            "$",
            ">",
            ">>",
            "<",
        ]

        if any(token in host_lower for token in tokens_prohibidos):
            resultado = "Comando no permitido"
        else:
            comando = f"ping -c 1 {host}"
            resultado = os.popen(comando).read()

    return render_template("ping.html", host=host, resultado=resultado)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

