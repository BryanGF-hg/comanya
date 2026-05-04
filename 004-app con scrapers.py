from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file
import mysql.connector
import os
import pandas as pd
from functools import wraps
from datetime import datetime

from scraper import run_scraper

app = Flask(__name__, template_folder="templates")
app.secret_key = "comanya123$"

# ------------------------
# CONFIG BD
# ------------------------
db_config = {
    "host": "localhost",
    "user": "comanya",
    "password": "comanya",
    "database": "comanya"
}

def get_db():
    conn = mysql.connector.connect(**db_config)
    return conn, conn.cursor(dictionary=True)

# ------------------------
# AUTH
# ------------------------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper

# ------------------------
# ROUTES
# ------------------------
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

@app.route("/backend")
@login_required
def backend():
    conn, cur = get_db()
    cur.execute("SELECT * FROM entrada ORDER BY id DESC")
    datos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template(
        "backend.html",
        datos=datos,
        role=session.get("role")   # ✅ CLAVE
    )

# ------------------------
# ANALIZAR (CLAVE)
# ------------------------
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


        # 🔹 Aquí llamarías a tu scraper/análisis real
        # Simulamos datos para el ejemplo
        class Dummy:
            def __init__(self, name):
                self.name = name
                self.city = ""
                self.province = provincia
                self.cnae = cnae
                self.total_score = 0.85
        lead = Dummy(empresa)

        top = [
            Dummy("Competidor A"),
            Dummy("Competidor B"),
            Dummy("Competidor C"),
        ]

        secondary = [
            Dummy("Competidor D"),
            Dummy("Competidor E"),
        ]

        # ✅ IMPORTANTE: devolver SOLO el fragmento
        return render_template(
            "fragmento_resultados.html",
            lead=lead,
            top=top,
            secondary=secondary,
            file_url=f"{empresa}_dummy.xlsx"
        )



        print(f"📊 Analizando: {empresa} | {cnae} | {provincia}")

        # SCRAPER
        data = run_scraper(
            company=empresa,
            cnae=cnae,
            provincia=provincia,
            empleados=empleados,
            facturacion=facturacion
        )

        # GENERAR EXCEL
        if not os.path.exists("output_excel"):
            os.makedirs("output_excel")

        filename = f"{empresa}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join("output_excel", filename)

        pd.DataFrame([data]).to_excel(filepath, index=False)
        data["archivo_excel"] = filepath

        # INSERT BD (100% COMPATIBLE)
        conn, cur = get_db()
        cur.execute("""
            INSERT INTO entrada
            (empresa, cnae, provincia, empleados, facturacion, archivo_excel)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            data["empresa"],
            data["cnae"],
            data["provincia"],
            data["empleados"],
            data["facturacion"],
            data["archivo_excel"]
        ))
        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Análisis completado correctamente")
        return redirect(url_for("backend"))

    except Exception as e:
        import traceback
        traceback.print_exc()
        flash(f"❌ Error: {e}")
        return redirect(url_for("backend"))

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
            "UPDATE entrada SET empresa=%s WHERE id=%s",
            (empresa, id_reg)
        )
        conn.commit()
        cur.close()
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

        # borrar excel si existe
        cur.execute("SELECT archivo_excel FROM entrada WHERE id=%s", (id,))
        row = cur.fetchone()
        if row and row["archivo_excel"] and os.path.exists(row["archivo_excel"]):
            os.remove(row["archivo_excel"])

        cur.execute("DELETE FROM entrada WHERE id=%s", (id,))
        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Registro eliminado")
    except Exception as e:
        flash(f"❌ Error: {e}")

    return redirect(url_for("backend"))

@app.route("/preview/<path:filename>")
@login_required
def preview(filename):
    try:
        if not os.path.exists(filename):
            return {"error": "Archivo no encontrado"}, 404

        df = pd.read_excel(filename).fillna("")
        df = df.head(20)

        return {
            "columnas": df.columns.tolist(),
            "filas": df.values.tolist(),
            "total": len(df)
        }
    except Exception as e:
        return {"error": str(e)}, 500
        
@app.route("/crear", methods=["POST"])
@login_required
def crear():
    if session.get("role") != "admin":
        flash("No autorizado")
        return redirect(url_for("backend"))

    try:
        empresa = request.form.get("empresa")
        cnae = request.form.get("cnae")
        provincia = request.form.get("provincia")

        conn, cur = get_db()
        cur.execute("""
            INSERT INTO entrada (empresa, cnae, provincia)
            VALUES (%s, %s, %s)
        """, (empresa, cnae, provincia))
        conn.commit()
        cur.close()
        conn.close()

        flash("✅ Registro creado")
    except Exception as e:
        flash(f"❌ Error: {e}")

    return redirect(url_for("backend"))         
# ------------------------
# DESCARGA
# ------------------------
@app.route("/download/<path:filename>")
@login_required
def download(filename):
    if os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    flash("Archivo no encontrado")
    return redirect(url_for("backend"))

# ------------------------
# MAIN
# ------------------------
if __name__ == "__main__":
    if not os.path.exists("output_excel"):
        os.makedirs("output_excel")

    print("🚀 004-app iniciado en http://localhost:5000")
    app.run(debug=True, port=5000, use_reloader=False)

