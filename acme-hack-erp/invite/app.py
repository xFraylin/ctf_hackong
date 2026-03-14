import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(CURRENT_DIR)
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)

from flask import Flask, render_template, request
from core_shared import inicializar_base_datos


app = Flask(__name__, template_folder="templates")
app.secret_key = "clave_super_secreta_123"

# Initialize database once at import time (replacing before_first_request hook)
inicializar_base_datos()


@app.route("/", methods=["GET", "POST"])
def index():
    """
    IntraCorp Partner Onboarding Portal.
    Includes the Invite Code form.
    """
    invite_code = None
    if request.method == "POST":
        invite_code = request.form.get("invite_code", "")
    return render_template("invite_home.html", invite_code=invite_code)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

