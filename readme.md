# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate  

# En Windows: 
  venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3.a Ejecutar análisis con main.py desde linea de comando
python main.py --company "MiEmpresa SL" --cnae 4662 --province Madrid --city Madrid --employees 50 --revenue 5 --output "mi_analisis.xlsx"

# 3.b Ejecutar análisis con run.py en un modo mas interactivo 

# Diferencias entre main.py y run.py: 
main.py → Es el motor/core del análisis (contiene toda la lógica de scraping, scoring, exportación)

run.py → Es solo la interfaz/interacción con el usuario (pide datos y llama a main.py)
