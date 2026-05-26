from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, session, send_file
)
import os
import sqlite3
import pandas as pd
from functools import wraps
from datetime import datetime

# ========================
# APP
# ========================
app = Flask(__name__, template_folder="templates")
app.secret_key = "comanya123$"

# ========================
# DATABASE (SQLite)
# ========================
def get_db():
    conn = sqlite3.connect("data.db")
    conn.row_factory = sqlite3.Row
    return conn, conn.cursor()

def init_db():
    conn = sqlite3.connect("data.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entrada (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            empresa TEXT,
            cnae TEXT,
            provincia TEXT,
            empleados INTEGER,
            facturacion REAL,
            archivo_excel TEXT
        )
    """)
    conn.commit()
    conn.close()

# ========================
# AUTH
# ========================
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ========================
# ROUTES
# ========================
@app.route("/")
def index():
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if u == "admin" and p == "admin123":
            session["user"] = "admin"
            session["role"] = "admin"
            return redirect(url_for("backend"))

        flash("Credenciales incorrectas")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ========================
# BACKEND
# ========================
@app.route("/backend")
@login_required
def backend():
    try:
        conn, cur = get_db()
        cur.execute("SELECT * FROM entrada ORDER BY id DESC")
        datos = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ Error BD: {e}")
        datos = []

    return render_template(
        "backend.html",
        datos=datos,
        role=session.get("role")
    )

# ========================
# ANALIZAR (MVP)
# ========================
@app.route("/analizar", methods=["POST"])
@login_required
def analizar():
    if session.get("role") != "admin":
        flash("Acceso denegado")
        return redirect(url_for("backend"))

    try:
        empresa = request.form.get("company")
        cnae = request.form.get("cnae")
        provincia = request.form.get("province")

        empleados = request.form.get("employees")
        empleados = int(empleados) if empleados and empleados.strip() else None

        facturacion = request.form.get("revenue")
        facturacion = float(facturacion) if facturacion and facturacion.strip() else None

        # ---- SIMULACIÓN DE RESULTADO ----
        if not os.path.exists("output_excel"):
            os.makedirs("output_excel")

        filename = f"{empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join("output_excel", filename)

        pd.DataFrame([{
            "empresa": empresa,
            "cnae": cnae,
            "provincia": provincia,
            "empleados": empleados,
            "facturacion": facturacion
        }]).to_excel(filepath, index=False)

        # ---- INSERT SQLITE ----
        conn, cur = get_db()
        cur.execute("""
            INSERT INTO entrada
            (empresa, cnae, provincia, empleados, facturacion, archivo_excel)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            empresa,
            cnae,
            provincia,
            empleados,
            facturacion,
            filepath
        ))
        conn.commit()
        conn.close()

        flash("✅ Análisis completado correctamente")
        return redirect(url_for("backend"))

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"❌ Error: {e}")
        return redirect(url_for("backend"))

# ========================
# CRUD
# ========================
@app.route("/actualizar", methods=["POST"])
@login_required
def actualizar():
    if session.get("role") != "admin":
        return {"error": "No autorizado"}, 403

    try:
        id_reg = request.form.get("id")
        empresa = request.form.get("empresa")

        conn, cur = get_db()
        cur.execute(
            "UPDATE entrada SET empresa=? WHERE id=?",
            (empresa, id_reg)
        )
        conn.commit()
        conn.close()

        return {"success": True}
    except Exception as e:
        return {"error": str(e)}, 500

@app.route("/eliminar/<int:id>")
@login_required
def eliminar(id):
    if session.get("role") != "admin":
        flash("No tienes permiso")
        return redirect(url_for("backend"))

    try:
        conn, cur = get_db()
        cur.execute("SELECT archivo_excel FROM entrada WHERE id=?", (id,))
        row = cur.fetchone()

        if row and row["archivo_excel"] and os.path.exists(row["archivo_excel"]):
            os.remove(row["archivo_excel"])

        cur.execute("DELETE FROM entrada WHERE id=?", (id,))
        conn.commit()
        conn.close()

        flash("✅ Registro eliminado")
    except Exception as e:
        flash(f"❌ Error: {e}")

    return redirect(url_for("backend"))

# ========================
# FILES
# ========================
@app.route("/download/<path:filename>")
@login_required
def download(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    flash("Archivo no encontrado")
    return redirect(url_for("backend"))

@app.route("/preview/<path:filename>")
@login_required
def preview(filename):
    try:
        if not os.path.exists(filename):
            return {"error": "Archivo no encontrado"}, 404

        df = pd.read_excel(filename).fillna("").head(20)

        return {
            "columnas": df.columns.tolist(),
            "filas": df.values.tolist(),
            "total": len(df)
        }
    except Exception as e:
        return {"error": str(e)}, 500

# ========================
# MAIN (RENDER READY)
# ========================
if __name__ == "__main__":
    if not os.path.exists("output_excel"):
        os.makedirs("output_excel")

    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
