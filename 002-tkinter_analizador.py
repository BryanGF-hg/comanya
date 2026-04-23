#!/usr/bin/env python3
"""
Competitor Analyzer - Interfaz Gráfica con Tkinter
Con búsqueda automática de CNAE desde InfoCif
"""

import os
import sys
import subprocess
import shutil
import threading
from datetime import datetime
import time
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import requests
from bs4 import BeautifulSoup
import re

# Configuración
OUTPUT_DIR = "output_excel"

class CNAESearcher:
    """Clase para buscar CNAE desde InfoCif"""
    
    def __init__(self):
        self.base_url = "https://www.infocif.es"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search_cnae_by_company(self, company_name: str) -> dict:
        """Busca el CNAE de una empresa por su nombre"""
        try:
            # Buscar la empresa
            search_url = f"{self.base_url}/buscar?q={company_name.replace(' ', '+')}"
            response = requests.get(search_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar enlaces a empresas
            company_links = soup.find_all('a', href=re.compile(r'/empresa/'))
            
            if not company_links:
                return {'success': False, 'error': 'No se encontró la empresa'}
            
            # Tomar el primer resultado
            first_link = company_links[0]
            company_url = first_link.get('href')
            if company_url:
                full_url = f"{self.base_url}{company_url}"
                return self._extract_cnae_from_page(full_url, company_name)
            
            return {'success': False, 'error': 'No se pudo acceder a los detalles'}
            
        except requests.RequestException as e:
            return {'success': False, 'error': f'Error de conexión: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Error inesperado: {str(e)}'}
    
    def _extract_cnae_from_page(self, url: str, company_name: str) -> dict:
        """Extrae el CNAE de la página de la empresa"""
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar CNAE en diferentes patrones
            cnae_patterns = [
                r'CNAE[:\s]*(\d{4})',
                r'Código CNAE[:\s]*(\d{4})',
                r'Actividad principal[:\s]*\w+\s*\((\d{4})\)',
                r'<td>CNAE</td>\s*<td>(\d{4})</td>',
                r'(\d{4})\s*-\s*[A-ZáéíóúñÑ\s]+'
            ]
            
            page_text = soup.get_text()
            
            for pattern in cnae_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    cnae = match.group(1)
                    # Validar que sea un CNAE válido (4 dígitos)
                    if cnae.isdigit() and len(cnae) == 4:
                        return {
                            'success': True,
                            'cnae': cnae,
                            'message': f'CNAE encontrado: {cnae}'
                        }
            
            # Buscar también en elementos específicos
            cnae_elements = soup.find_all(text=re.compile(r'CNAE', re.IGNORECASE))
            for elem in cnae_elements:
                parent = elem.find_parent()
                if parent:
                    next_elem = parent.find_next_sibling()
                    if next_elem:
                        text = next_elem.get_text()
                        cnae_match = re.search(r'(\d{4})', text)
                        if cnae_match:
                            cnae = cnae_match.group(1)
                            return {
                                'success': True,
                                'cnae': cnae,
                                'message': f'CNAE encontrado: {cnae}'
                            }
            
            return {'success': False, 'error': 'No se encontró el código CNAE en la página'}
            
        except Exception as e:
            return {'success': False, 'error': f'Error extrayendo datos: {str(e)}'}


class CompetitorAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Competitor Analyzer - Análisis de Competidores")
        self.root.geometry("750x850")
        self.root.resizable(True, True)
        
        # Inicializar buscador de CNAE
        self.cnae_searcher = CNAESearcher()
        
        # Configurar estilo
        self.setup_styles()
        
        # Variables
        self.company_var = tk.StringVar()
        self.cnae_var = tk.StringVar()
        self.province_var = tk.StringVar()
        self.city_var = tk.StringVar()
        self.employees_var = tk.StringVar()
        self.revenue_var = tk.StringVar()
        
        # Variable para tracking de búsqueda
        self.searching_cnae = False
        
        # Crear widgets
        self.create_widgets()
        
        # Asegurar carpeta de salida
        self.ensure_output_dir()
    
    def setup_styles(self):
        """Configurar estilos y colores"""
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#34495e',
            'success': '#27ae60',
            'danger': '#e74c3c',
            'warning': '#f39c12',
            'info': '#3498db',
            'light': '#ecf0f1',
            'dark': '#2c3e50'
        }
        
        # Configurar estilo para ttk
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores
        style.configure('TLabel', background='#f0f0f0', foreground='#2c3e50', font=('Arial', 10))
        style.configure('TButton', font=('Arial', 10, 'bold'), padding=5)
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabelframe', background='#f0f0f0', font=('Arial', 10, 'bold'))
        style.configure('TLabelframe.Label', background='#f0f0f0', foreground='#2c3e50')
    
    def ensure_output_dir(self):
        """Asegura que la carpeta de salida existe"""
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
    
    def search_cnae(self):
        """Buscar CNAE automáticamente desde InfoCif"""
        company_name = self.company_var.get().strip()
        
        if not company_name:
            messagebox.showwarning("Nombre requerido", 
                                 "Por favor, ingrese el nombre de la empresa antes de buscar el CNAE")
            return
        
        if self.searching_cnae:
            return
        
        # Deshabilitar botón durante la búsqueda
        self.search_cnae_btn.config(state='disabled', text='🔍 Buscando...')
        self.searching_cnae = True
        
        # Ejecutar búsqueda en hilo separado
        thread = threading.Thread(target=self._search_cnae_thread, args=(company_name,))
        thread.daemon = True
        thread.start()
    
    def _search_cnae_thread(self, company_name):
        """Ejecuta la búsqueda de CNAE en un hilo"""
        try:
            result = self.cnae_searcher.search_cnae_by_company(company_name)
            
            if result['success']:
                cnae = result['cnae']
                self.root.after(0, self._update_cnae_field, cnae, result['message'])
            else:
                self.root.after(0, self._show_search_error, result['error'])
                
        except Exception as e:
            self.root.after(0, self._show_search_error, str(e))
        finally:
            self.root.after(0, self._enable_search_button)
    
    def _update_cnae_field(self, cnae, message):
        """Actualiza el campo CNAE con el valor encontrado"""
        self.cnae_var.set(cnae)
        self.status_label.config(text=f"✅ {message}", foreground=self.colors['success'])
        
        # Mostrar mensaje de éxito
        messagebox.showinfo("CNAE Encontrado", 
                           f"Se ha encontrado el código CNAE: {cnae}\n\n{message}")
        
        # Limpiar mensaje después de 3 segundos
        self.root.after(3000, lambda: self.status_label.config(text=""))
    
    def _show_search_error(self, error):
        """Muestra error de búsqueda"""
        self.status_label.config(text=f"⚠️ Error: {error}", foreground=self.colors['warning'])
        
        # Preguntar si quiere ingresar manualmente
        if messagebox.askyesno("CNAE No Encontrado", 
                              f"No se pudo encontrar el CNAE automáticamente.\n\n"
                              f"Error: {error}\n\n"
                              f"¿Desea ingresar el código CNAE manualmente?"):
            # Enfocar el campo CNAE para entrada manual
            self.cnae_entry.focus()
        else:
            messagebox.showinfo("Entrada Manual", 
                              "Puede buscar el código CNAE en:\n\n"
                              "• https://www.cnae.com.es/\n"
                              "• https://www.ine.es/clasifi/cnae2009.htm\n\n"
                              "Luego ingréselo manualmente en el campo.")
        
        # Limpiar mensaje después de 5 segundos
        self.root.after(5000, lambda: self.status_label.config(text=""))
    
    def _enable_search_button(self):
        """Rehabilita el botón de búsqueda"""
        self.search_cnae_btn.config(state='normal', text='🔍 Buscar CNAE')
        self.searching_cnae = False
    
    def create_widgets(self):
        """Crear todos los widgets de la interfaz"""
        # Frame principal con scroll
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Título
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text="🚀 COMPETITOR ANALYZER", 
                                font=('Arial', 18, 'bold'), foreground=self.colors['primary'])
        title_label.pack()
        
        subtitle_label = ttk.Label(title_frame, text="Análisis inteligente de competidores", 
                                   font=('Arial', 10), foreground=self.colors['secondary'])
        subtitle_label.pack()
        
        # Separador
        ttk.Separator(main_frame, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Frame para datos de la empresa
        data_frame = ttk.LabelFrame(main_frame, text="📝 Datos de la Empresa", padding=15)
        data_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Campos obligatorios
        # Nombre (con botón de búsqueda)
        ttk.Label(data_frame, text="🏢 Nombre de la empresa *", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        name_frame = ttk.Frame(data_frame)
        name_frame.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        company_entry = ttk.Entry(name_frame, textvariable=self.company_var, width=40, font=('Arial', 10))
        company_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botón para buscar CNAE automáticamente
        self.search_cnae_btn = ttk.Button(name_frame, text="🔍 Buscar CNAE", 
                                          command=self.search_cnae, width=15)
        self.search_cnae_btn.pack(side=tk.LEFT)
        
        # Tooltip para el botón
        self.create_tooltip(self.search_cnae_btn, 
                           "Busca automáticamente el código CNAE\n"
                           "de la empresa en InfoCif")
        
        # CNAE
        ttk.Label(data_frame, text="🔢 Código CNAE *", font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        cnae_frame = ttk.Frame(data_frame)
        cnae_frame.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        self.cnae_entry = ttk.Entry(cnae_frame, textvariable=self.cnae_var, width=40, font=('Arial', 10))
        self.cnae_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Botón para limpiar CNAE
        clear_cnae_btn = ttk.Button(cnae_frame, text="🗑️ Limpiar", 
                                   command=lambda: self.cnae_var.set(""), width=10)
        clear_cnae_btn.pack(side=tk.LEFT)
        
        ttk.Label(data_frame, text="Ej: 4662, 6201, 4121", font=('Arial', 8), 
                 foreground=self.colors['secondary']).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Provincia
        ttk.Label(data_frame, text="📍 Provincia *", font=('Arial', 10, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=5)
        province_entry = ttk.Entry(data_frame, textvariable=self.province_var, width=50, font=('Arial', 10))
        province_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Separador
        ttk.Separator(data_frame, orient='horizontal').grid(row=4, column=0, columnspan=2, sticky=tk.EW, pady=15)
        
        # Campos opcionales
        ttk.Label(data_frame, text="📊 Datos Opcionales", font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        
        # Ciudad
        ttk.Label(data_frame, text="🏙️ Ciudad", font=('Arial', 10)).grid(row=6, column=0, sticky=tk.W, pady=5)
        city_entry = ttk.Entry(data_frame, textvariable=self.city_var, width=50, font=('Arial', 10))
        city_entry.grid(row=6, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Empleados
        ttk.Label(data_frame, text="👥 Número de empleados", font=('Arial', 10)).grid(row=7, column=0, sticky=tk.W, pady=5)
        employees_entry = ttk.Entry(data_frame, textvariable=self.employees_var, width=50, font=('Arial', 10))
        employees_entry.grid(row=7, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Facturación
        ttk.Label(data_frame, text="💶 Facturación (millones €)", font=('Arial', 10)).grid(row=8, column=0, sticky=tk.W, pady=5)
        revenue_entry = ttk.Entry(data_frame, textvariable=self.revenue_var, width=50, font=('Arial', 10))
        revenue_entry.grid(row=8, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Frame para botones principales
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=15)
        
        # Botón Analizar
        self.analyze_btn = ttk.Button(button_frame, text="🔍 ANALIZAR COMPETIDORES", 
                                       command=self.analyze, style='Accent.TButton')
        self.analyze_btn.pack(side=tk.LEFT, padx=5)
        
        # Configurar estilo del botón principal
        style = ttk.Style()
        style.configure('Accent.TButton', background=self.colors['success'], foreground='white')
        
        # Botón Limpiar todo
        clear_all_btn = ttk.Button(button_frame, text="🗑️ Limpiar Todo", command=self.clear_fields)
        clear_all_btn.pack(side=tk.LEFT, padx=5)
        
        # Etiqueta de estado
        self.status_label = ttk.Label(main_frame, text="", font=('Arial', 9))
        self.status_label.pack(fill=tk.X, pady=5)
        
        # Frame para progreso
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')
        
        # Frame para resultados
        results_frame = ttk.LabelFrame(main_frame, text="📋 Resultados", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Área de texto con scroll para resultados
        self.results_text = scrolledtext.ScrolledText(results_frame, height=12, wrap=tk.WORD, 
                                                       font=('Courier', 9), bg='#2c3e50', fg='#ecf0f1')
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Configurar tags para colores en resultados
        self.results_text.tag_config('success', foreground='#27ae60')
        self.results_text.tag_config('error', foreground='#e74c3c')
        self.results_text.tag_config('info', foreground='#3498db')
        self.results_text.tag_config('warning', foreground='#f39c12')
        
        # Frame para información de salida
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(10, 0))
        
        output_label = ttk.Label(info_frame, text=f"📁 Los resultados se guardarán en: {OUTPUT_DIR}/", 
                                 font=('Arial', 8), foreground=self.colors['secondary'])
        output_label.pack()
        
        # Vincular Enter para ejecutar análisis
        self.root.bind('<Return>', lambda event: self.analyze())
    
    def create_tooltip(self, widget, text):
        """Crea un tooltip simple para un widget"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = ttk.Label(tooltip, text=text, background='#ffffe0', relief='solid', borderwidth=1)
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            widget.tooltip = tooltip
            widget.bind('<Leave>', lambda e: hide_tooltip())
        
        widget.bind('<Enter>', show_tooltip)
    
    def clear_fields(self):
        """Limpiar todos los campos"""
        self.company_var.set("")
        self.cnae_var.set("")
        self.province_var.set("")
        self.city_var.set("")
        self.employees_var.set("")
        self.revenue_var.set("")
        self.results_text.delete(1.0, tk.END)
        self.status_label.config(text="")
    
    def log_message(self, message, tag=None):
        """Agregar mensaje al área de resultados"""
        self.results_text.insert(tk.END, message + "\n", tag)
        self.results_text.see(tk.END)
        self.root.update_idletasks()
    
    def find_latest_excel(self):
        """Encuentra el archivo Excel más reciente"""
        excel_files = [f for f in os.listdir('.') if f.endswith('.xlsx') and f.startswith('competitor_analysis_')]
        if not excel_files:
            return None
        excel_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return excel_files[0]
    
    def move_to_output_folder(self, source_file):
        """Mueve el archivo a la carpeta output_excel"""
        if not os.path.exists(source_file):
            return source_file
        
        filename = os.path.basename(source_file)
        dest_file = os.path.join(OUTPUT_DIR, filename)
        
        if os.path.exists(dest_file):
            name, ext = os.path.splitext(filename)
            timestamp = datetime.now().strftime('%H%M%S')
            filename = f"{name}_{timestamp}{ext}"
            dest_file = os.path.join(OUTPUT_DIR, filename)
        
        try:
            shutil.move(source_file, dest_file)
            return dest_file
        except Exception as e:
            return source_file
    
    def run_analysis_thread(self, company, cnae, province, city, employees, revenue):
        """Ejecuta el análisis en un hilo separado"""
        cmd = [
            sys.executable, 'main.py',
            '--company', company,
            '--cnae', cnae,
            '--province', province
        ]
        
        if city:
            cmd.extend(['--city', city])
        if employees:
            cmd.extend(['--employees', str(employees)])
        if revenue:
            cmd.extend(['--revenue', str(revenue)])
        
        try:
            # Ejecutar main.py
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Buscar el archivo Excel generado
                time.sleep(1)
                latest_excel = self.find_latest_excel()
                
                if latest_excel:
                    final_path = self.move_to_output_folder(latest_excel)
                    self.root.after(0, self.on_analysis_success, final_path, result.stdout)
                else:
                    self.root.after(0, self.on_analysis_error, "No se encontró el archivo Excel generado")
            else:
                self.root.after(0, self.on_analysis_error, result.stderr or "Error desconocido")
                
        except Exception as e:
            self.root.after(0, self.on_analysis_error, str(e))
        finally:
            self.root.after(0, self.stop_progress)
    
    def on_analysis_success(self, file_path, output):
        """Manejar éxito del análisis"""
        self.log_message("", "success")
        self.log_message("=" * 60, "success")
        self.log_message("✅ ANÁLISIS COMPLETADO EXITOSAMENTE", "success")
        self.log_message("=" * 60, "success")
        self.log_message(f"📁 Resultado guardado en: {file_path}", "info")
        self.log_message("", "")
        self.log_message("📊 Resumen del análisis:", "info")
        
        # Mostrar últimas líneas del output
        lines = output.split('\n')
        for line in lines[-15:]:
            if '✅' in line or '✨' in line or '📋' in line:
                self.log_message(line, "success")
            elif '⚠️' in line:
                self.log_message(line, "warning")
            elif '❌' in line:
                self.log_message(line, "error")
            elif line.strip():
                self.log_message(line, "info")
        
        messagebox.showinfo("Éxito", f"Análisis completado exitosamente!\n\nResultado guardado en:\n{file_path}")
    
    def on_analysis_error(self, error_msg):
        """Manejar error del análisis"""
        self.log_message("", "error")
        self.log_message("=" * 60, "error")
        self.log_message("❌ ERROR EN EL ANÁLISIS", "error")
        self.log_message("=" * 60, "error")
        self.log_message(f"Error: {error_msg}", "error")
        
        messagebox.showerror("Error", f"Error en el análisis:\n\n{error_msg}")
    
    def start_progress(self):
        """Iniciar barra de progreso"""
        self.progress_bar.pack(fill=tk.X, pady=5)
        self.progress_bar.start(10)
        self.analyze_btn.config(state='disabled')
        self.search_cnae_btn.config(state='disabled')
        self.status_label.config(text="🔄 Analizando competidores... Por favor espere")
        self.results_text.delete(1.0, tk.END)
        self.log_message("🚀 INICIANDO ANÁLISIS DE COMPETIDORES", "info")
        self.log_message("=" * 60, "info")
        self.log_message("")
    
    def stop_progress(self):
        """Detener barra de progreso"""
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.analyze_btn.config(state='normal')
        self.search_cnae_btn.config(state='normal')
        self.status_label.config(text="✅ Análisis completado")
        self.root.after(3000, lambda: self.status_label.config(text=""))
    
    def analyze(self):
        """Validar datos y ejecutar análisis"""
        # Validar campos obligatorios
        company = self.company_var.get().strip()
        if not company:
            messagebox.showwarning("Campos incompletos", "Por favor ingrese el nombre de la empresa")
            return
        
        cnae = self.cnae_var.get().strip()
        if not cnae:
            messagebox.showwarning("Campos incompletos", "Por favor ingrese el código CNAE\n\nPuede usar el botón 'Buscar CNAE' para obtenerlo automáticamente")
            return
        
        # Validar que CNAE sea numérico de 4 dígitos
        if not cnae.isdigit() or len(cnae) != 4:
            if not messagebox.askyesno("CNAE Inválido", 
                                      f"El código CNAE '{cnae}' no parece válido (deben ser 4 dígitos).\n\n"
                                      f"¿Desea continuar de todos modos?"):
                return
        
        province = self.province_var.get().strip()
        if not province:
            messagebox.showwarning("Campos incompletos", "Por favor ingrese la provincia")
            return
        
        # Datos opcionales
        city = self.city_var.get().strip() or None
        employees = None
        revenue = None
        
        if self.employees_var.get().strip():
            try:
                employees = int(self.employees_var.get().strip())
            except ValueError:
                messagebox.showwarning("Dato inválido", "El número de empleados debe ser un valor numérico")
                return
        
        if self.revenue_var.get().strip():
            try:
                revenue = float(self.revenue_var.get().strip().replace(',', '.'))
            except ValueError:
                messagebox.showwarning("Dato inválido", "La facturación debe ser un valor numérico")
                return
        
        # Mostrar resumen
        summary = f"""
📋 RESUMEN DEL ANÁLISIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏢 Empresa: {company}
🔢 CNAE: {cnae}
📍 Provincia: {province}
"""
        if city:
            summary += f"🏙️ Ciudad: {city}\n"
        if employees:
            summary += f"👥 Empleados: {employees}\n"
        if revenue:
            summary += f"💶 Facturación: {revenue} M€\n"
        
        if not messagebox.askyesno("Confirmar Análisis", f"{summary}\n\n¿Desea ejecutar el análisis?"):
            return
        
        # Iniciar progreso
        self.start_progress()
        
        # Ejecutar análisis en hilo separado
        thread = threading.Thread(target=self.run_analysis_thread, 
                                   args=(company, cnae, province, city, employees, revenue))
        thread.daemon = True
        thread.start()


def main():
    root = tk.Tk()
    
    # Configurar ventana principal
    root.configure(bg='#f0f0f0')
    
    # Centrar ventana
    window_width = 800
    window_height = 900
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - window_width) // 2
    y = (screen_height - window_height) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    
    # Verificar que existe main.py
    if not os.path.exists('main.py'):
        messagebox.showerror("Error", "No se encuentra main.py en el directorio actual")
        sys.exit(1)
    
    app = CompetitorAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
