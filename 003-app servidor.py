from flask import Flask, render_template, request, send_file, flash, redirect, url_for, jsonify, session
import mysql.connector
import os
import sys
import pandas as pd
from functools import wraps
from datetime import datetime
import shutil
import importlib

# Añadir el directorio actual al path para poder importar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar el analizador desde 002-analizador.py (el que tiene Selenium)
try:
    # Usar importlib para importar el archivo
    spec = importlib.util.spec_from_file_location("analizador", "002-analizador.py")
    analizador_modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(analizador_modulo)
    CompetitorAnalyzer = analizador_modulo.CompetitorAnalyzer
    print("✅ Analizador importado correctamente desde 002-analizador.py")
except Exception as e:
    print(f"❌ Error importando 002-analizador.py: {e}")
    
    # Clase dummy como fallback
    class CompetitorAnalyzer:
        def __init__(self):
            print("⚠️ Usando analizador dummy - Conecta con el analizador real")
        def analyze(self, company_name, cnae, province, city=None, employees=None, revenue=None):
            from models.company import Company
            lead = Company(company_name, cnae, city or "", province)
            lead.employees = employees
            lead.revenue = revenue
            
            class DummyAnalysis:
                lead_company = lead
                top_competitors = []
                secondary_competitors = []
            return DummyAnalysis()
        def export_results(self, analysis):
            filename = f"dummy_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            df = pd.DataFrame({'Mensaje': ['Análisis dummy - Conecta el analizador real']})
            df.to_excel(filename, index=False)
            return filename

appservidor = Flask(__name__, template_folder=os.path.abspath('templates'))
appservidor.secret_key = "comanya123$"

db_config = {
    'host': 'localhost',
    'user': 'comanya',
    'password': 'comanya',
    'database': 'comanya'
}

def get_db():
    try:
        conn = mysql.connector.connect(**db_config)
        return conn, conn.cursor(dictionary=True)
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return None, None

# Inicializar Scraper
try:
    analyzer = CompetitorAnalyzer()
    print("✅ Analizador inicializado correctamente")
except Exception as e:
    print(f"❌ Error inicializando analizador: {e}")
    analyzer = None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@appservidor.route('/')
def index():
    return redirect(url_for('login'))

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
    if conn and cursor:
        cursor.execute("SELECT * FROM entrada ORDER BY id DESC")
        datos = cursor.fetchall()
        cursor.close()
        conn.close()
    else:
        datos = []
    return render_template('backend.html', datos=datos, role=session.get('role'))

@appservidor.route('/analizar', methods=['POST'])
@login_required
def analizar():
    if session.get('role') != 'admin':
        flash("Acceso denegado. Solo administradores pueden analizar.")
        return redirect(url_for('backend'))
    
    if not analyzer:
        flash("Error: El analizador no está disponible")
        return redirect(url_for('backend'))
    
    try:
        company = request.form.get('company')
        cnae = request.form.get('cnae')
        province = request.form.get('province')
        city = request.form.get('city') or None
        
        employees = request.form.get('employees')
        employees = int(employees) if employees and employees.strip() else None
        
        revenue = request.form.get('revenue')
        revenue = float(revenue) if revenue and revenue.strip() else None

        print(f"📊 Analizando: {company} | CNAE: {cnae} | {province} | {city}")

        # Ejecutar análisis en modo headless (sin ventana)
        analysis = analyzer.analyze(
            company_name=company, 
            cnae=cnae, 
            province=province, 
            city=city, 
            employees=employees, 
            revenue=revenue
        )
        
        output_file = analyzer.export_results(analysis)
        filename = os.path.basename(output_file)
        
        # Mover a output_excel
        dest_path = os.path.join("output_excel", filename)
        if os.path.exists(output_file) and not os.path.exists(dest_path):
            shutil.move(output_file, dest_path)
            filename = dest_path
        elif not os.path.exists(output_file):
            output_file = os.path.join("output_excel", filename)
            if os.path.exists(output_file):
                filename = output_file

        # Guardar en BD
        conn, cursor = get_db()
        if conn and cursor:
            query = """INSERT INTO entrada 
                       (empresa, cnae, provincia, ciudad, empleados, facturacion, archivo_excel, fecha_analisis) 
                       VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())"""
            values = (company, cnae, province, city, employees, revenue, filename)
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            print(f"✅ Guardado en BD: {filename}")

        return render_template('resultados.html', 
                               lead=analysis.lead_company, 
                               top=analysis.top_competitors, 
                               secondary=analysis.secondary_competitors,
                               file_url=filename)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        flash(f"Error en el análisis: {str(e)}")
        return redirect(url_for('backend'))

@appservidor.route('/actualizar', methods=['POST'])
@login_required
def actualizar():
    if session.get('role') != 'admin':
        return jsonify({"error": "No permitido"}), 403
    
    try:
        id_reg = request.form.get('id')
        nombre = request.form.get('empresa')
        conn, cursor = get_db()
        if conn and cursor:
            cursor.execute("UPDATE entrada SET empresa=%s WHERE id=%s", (nombre, id_reg))
            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({"success": True}), 200
        return jsonify({"error": "Error de BD"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@appservidor.route('/eliminar/<int:id>')
@login_required
def eliminar(id):
    if session.get('role') != 'admin':
        flash("No tienes permiso para eliminar")
        return redirect(url_for('backend'))
    
    try:
        conn, cursor = get_db()
        if conn and cursor:
            cursor.execute("SELECT archivo_excel FROM entrada WHERE id = %s", (id,))
            res = cursor.fetchone()
            if res and res.get('archivo_excel'):
                filepath = res['archivo_excel']
                if os.path.exists(filepath):
                    os.remove(filepath)
                elif os.path.exists(os.path.join("output_excel", os.path.basename(filepath))):
                    os.remove(os.path.join("output_excel", os.path.basename(filepath)))
            
            cursor.execute("DELETE FROM entrada WHERE id = %s", (id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash("Registro eliminado con éxito")
    except Exception as e:
        flash(f"Error al eliminar: {e}")
    return redirect(url_for('backend'))

@appservidor.route('/enriquecer', methods=['POST'])
@login_required
def enriquecer():
    """Endpoint para enriquecer datos de un competidor"""
    try:
        data = request.get_json()
        company_name = data.get('name')
        province = data.get('province')
        
        from scrapers.contact_scraper import ContactScraper
        contact_scraper = ContactScraper(config)
        
        contact_info = contact_scraper.search_contact_info(company_name, province)
        
        return jsonify({
            'phone': contact_info.get('phone', 'No encontrado'),
            'email': contact_info.get('email', 'No encontrado'),
            'website': contact_info.get('website', 'No encontrado')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@appservidor.route('/download/<path:filename>')
@login_required
def download_file(filename):
    possible_paths = [
        filename,
        os.path.join("output_excel", filename),
        os.path.join("output_excel", os.path.basename(filename))
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return send_file(path, as_attachment=True, download_name=os.path.basename(path))
    
    flash("Archivo no encontrado")
    return redirect(url_for('backend'))
    
@appservidor.route('/preview/<path:filename>')
@login_required
def preview_excel(filename):
    try:
        possible_paths = [
            filename,
            os.path.join("output_excel", filename),
            os.path.join("output_excel", os.path.basename(filename))
        ]
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        if not file_path:
            return jsonify({"error": "Archivo no encontrado"}), 404
        
        df = pd.read_excel(file_path)
        df = df.fillna("")
        df_display = df.head(20)
        
        data = {
            "columnas": df_display.columns.tolist(),
            "filas": df_display.values.tolist(),
            "total_filas": len(df),
            "nombre_archivo": os.path.basename(file_path)
        }
        return jsonify(data)
    except Exception as e:
        print(f"Error preview: {e}")
        return jsonify({"error": str(e)}), 500

def init_database():
    conn, cursor = get_db()
    if conn and cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS entrada (
                id INT AUTO_INCREMENT PRIMARY KEY,
                empresa VARCHAR(255) NOT NULL,
                cnae VARCHAR(10) NOT NULL,
                provincia VARCHAR(100) NOT NULL,
                ciudad VARCHAR(100),
                empleados INT,
                facturacion DECIMAL(10,2),
                archivo_excel VARCHAR(255),
                fecha_analisis DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("✅ Base de datos inicializada")

if __name__ == '__main__':
    if not os.path.exists("output_excel"):
        os.makedirs("output_excel")
        print("📁 Carpeta output_excel creada")
    
    init_database()
    
    print("🚀 Servidor iniciado en http://localhost:5000")
    appservidor.run(debug=True, port=5000, use_reloader=False)
