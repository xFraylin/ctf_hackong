import os
import sys
import base64

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Flask, request, render_template
from core_shared import obtener_conexion, inicializar_base_datos, FLAG_LFI


app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta_123"

# Initialize database once at import time (replacing before_first_request hook)
inicializar_base_datos()


@app.route("/")
def index():
    """
    IntraCorp Document Repository landing page.
    """
    # List documents from uploads directory, but show fixed names in UI.
    documentos = [
        "employee_contract_2026.pdf",
        "internal_policy_handbook.pdf",
        "audit_report_q1.pdf",
        "marketing_strategy_draft.pdf",
        "engineering_notes.txt",
    ]

    # Build base64 IDs for each document name
    docs_with_ids = []
    for nombre in documentos:
        doc_id = base64.b64encode(nombre.encode("utf-8")).decode("utf-8")
        docs_with_ids.append({"nombre": nombre, "doc_id": doc_id})

    return render_template("documents.html", documentos=docs_with_ids)


@app.route("/api/document")
def api_document():
    """
    VULNERABLE DOCUMENT ENDPOINT

    Path: /api/document?doc_id=BASE64

    This preserves the Local File Inclusion style vulnerability from the
    original /descargar endpoint, adapted to use a base64-encoded parameter.
    """
    doc_id = request.args.get("doc_id", "")

    if not doc_id:
        return "Documento no especificado", 400

    try:
        archivo = base64.b64decode(doc_id).decode("utf-8")
    except Exception as e:
        return f"Error al decodificar ID de documento: {e}", 400

    # VULNERABILIDAD: LFI - Local File Inclusion
    # No valida ni sanitiza la ruta del archivo
    ruta_archivo = os.path.join("uploads", archivo)

    try:
        with open(ruta_archivo, "r") as f:
            contenido = f.read()
        # Mantener el estilo simple de la respuesta vulnerable
        return f"<pre>{contenido}</pre>"
    except Exception as e:
        return f"Error al leer archivo: {str(e)}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

