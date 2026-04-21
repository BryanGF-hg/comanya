import pandas as pd
import os
from typing import List, Dict
from datetime import datetime
from models.company import Company
import xlsxwriter

class ExcelExporter:
    def __init__(self, config):
        self.config = config
        # Definimos la carpeta de salida
        self.output_dir = "output_excel"
        # Creamos la carpeta si no existe al iniciar
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def export_to_excel(self, lead_company: Company, competitors_result: Dict[str, List[Company]], 
                        filename: str = "competitor_analysis.xlsx"):
        """Exporta el análisis a Excel dentro de la carpeta output_excel"""
        
        # Construimos la ruta completa
        full_path = os.path.join(self.output_dir, filename)
        
        # Usamos el mapeo dinámico para que sea fácil ampliar campos
        field_mapping = {
            'Empresa': 'name',
            'Teléfono': 'phone',
            'Email': 'email',
            'Gerente Empresa': 'manager_name',
            'Poblacion': 'city',
            'Descripcion de GMaps': 'gm_description',
            'Licita(Si/No/?)': 'bids_active',
            'Motivo': 'score_motive',
            'Web': 'website',
            'Dirección': 'address',
            'Municipio': 'city',
            'CNAE': 'cnae',
            'Empleados': 'employees',
            'Facturación(M€)': 'revenue',
            'Score': 'total_score',
            'Score_Reviews_Google': 'google_reviews',
            'Crecimiento(%)': 'growth',
            'Decrecimiento(%)': 'decrease',
            'Tendencia': 'tendency'
        }

        # Combinamos todos los competidores para la estructura vertical que pediste
        competitors = competitors_result.get('top', []) + competitors_result.get('secondary', [])
        
        # Estructura Vertical: Primera columna son los nombres de los campos
        export_data = {'Campo': list(field_mapping.keys())}
        
        # Añadimos una columna por cada competidor (Competidor 1, Competidor 2...)
        for i, comp in enumerate(competitors, 1):
            col_name = f"Competidor {i}"
            col_values = []
            for label, attr in field_mapping.items():
                val = getattr(comp, attr, "")
                if val is None: val = ""
                # Redondeo automático si es número
                if isinstance(val, (float, int)) and "Score" in label:
                    val = round(val, 4)
                col_values.append(val)
            export_data[col_name] = col_values

        df = pd.DataFrame(export_data)

        # Guardado con XlsxWriter para auto-ajuste y formato
        with pd.ExcelWriter(full_path, engine='xlsxwriter') as writer:
            df.to_excel(writer, sheet_name='Análisis', index=False)
            
            workbook = writer.book
            worksheet = writer.sheets['Análisis']
            
            # Formato para la primera columna (nombres de campos)
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            
            # Ajuste de ancho de columnas
            for i, col in enumerate(df.columns):
                column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, min(column_len, 50))
                
        return full_path