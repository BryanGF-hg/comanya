from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify, session
import mysql.connector
import os
import pandas as pd
import importlib
from functools import wraps

# Importación dinámica del analizador
try: 
    analizador_modulo = importlib.import_module("002-analizador")
    CompetitorAnalyzer = analizador_modulo.CompetitorAnalyzer
except Exception as e:
    print(f"Error importando 002-analizador: {e}")

appservidor = Flask(__name__, template_folder=os.path.abspath('templates'))
appservidor.secret_key = "comanya123$"

db_config = {
    'host': 'localhost', 'user': 'comanya', 'password': 'comanya', 'database': 'comanya'
}

def get_db():
    conn = mysql.connector.connect(**db_config)
    return conn, conn.cursor(dictionary=True)

# Inicializar Scraper
analyzer = CompetitorAnalyzer()

# Decorador para proteger rutas
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
    
@appservidor.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        password = request.form.get('password')
        
        if user == 'admin' and password == 'admin123':
            session['user'] = 'admin'
            session['role'] = 'admin'
            return redirect(url_for('backend'))
        elif user == 'comanya' and password == 'user123':
            session['user'] = 'comanya'
            session['role'] = 'user'
            return redirect(url_for('backend'))
        else:
            flash('Credenciales incorrectas')
            
    return render_template('login.html')

@appservidor.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@appservidor.route('/backend')
@login_required
def backend():
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM entrada ORDER BY id DESC")
    datos = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('backend.html', datos=datos, role=session.get('role'))

@appservidor.route('/analizar', methods=['POST'])
@login_required
def analizar():
    if session.get('role') != 'admin':
        return "Acceso denegado", 403
    try:
        # 1. Extraer datos
        company = request.form.get('company')
        cnae = request.form.get('cnae')
        province = request.form.get('province')
        city = request.form.get('city') or ""
        
        employees = int(request.form.get('employees') or 0)
        revenue = float(request.form.get('revenue') or 0.0)

        # 2. Ejecutar análisis real
        analysis = analyzer.analyze(
            company_name=company, 
            cnae=cnae, 
            province=province, 
            city=city, 
            employees=employees, 
            revenue=revenue
        )
        
        # 3. Exportar
        output_file = analyzer.export_results(analysis)
        filename = os.path.basename(output_file)

        # 4. Guardar en Base de Datos
        conn, cursor = get_db()
        query = """INSERT INTO entrada 
                   (empresa, cnae, provincia, empleados, facturacion, archivo_excel) 
                   VALUES (%s, %s, %s, %s, %s, %s)"""
        values = (company, cnae, province, employees, revenue, filename)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
        conn.close()

        return render_template('resultados.html', 
                               lead=analysis.lead_company, 
                               top=analysis.top_competitors, 
                               secondary=analysis.secondary_competitors,
                               file_url=filename)

    except Exception as e:
        print(f"Error detallado: {e}")
        return f"Error en el análisis: {str(e)}", 500

@appservidor.route('/actualizar', methods=['POST'])
@login_required
def actualizar():
    if session.get('role') != 'admin':
        return "No permitido", 403
    try:
        id_reg = request.form.get('id')
        nombre = request.form.get('empresa')
        conn, cursor = get_db()
        cursor.execute("UPDATE entrada SET empresa=%s WHERE id=%s", (nombre, id_reg))
        conn.commit()
        cursor.close()
        conn.close()
        return "OK", 200
    except Exception as e:
        return str(e), 500

@appservidor.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    if session.get('role') != 'admin':
        flash("No tienes permiso para eliminar")
        return redirect(url_for('backend'))
    try:
        conn, cursor = get_db()
        cursor.execute("SELECT archivo_excel FROM entrada WHERE id = %s", (id,))
        res = cursor.fetchone()
        if res and res['archivo_excel']:
            path = os.path.join("output_excel", res['archivo_excel'])
            if os.path.exists(path): os.remove(path)
        
        cursor.execute("DELETE FROM entrada WHERE id = %s", (id,))
        conn.commit()
        cursor.close()
        conn.close()
        flash("Registro eliminado con éxito")
    except Exception as e:
        flash(f"Error al eliminar: {e}")
    return redirect(url_for('backend'))

@appservidor.route('/download/<filename>')
@login_required
def download_file(filename):
    path = os.path.join("output_excel", filename)
    return send_file(path, as_attachment=True)
    
@appservidor.route('/preview/<filename>')
@login_required
def preview_excel(filename):
    try:
        path = os.path.join("output_excel", filename)
        df = pd.read_excel(path)
        df = df.fillna("")
        data = {
            "columnas": df.columns.tolist(),
            "filas": df.values.tolist()
        }
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists("output_excel"):
        os.makedirs("output_excel")
    appservidor.run(debug=True, port=5000)
