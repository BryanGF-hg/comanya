#!/usr/bin/env python3
"""
Competitor Analyzer MVP - Análisis de competidores para PYMES
"""

import sys
import os
import yaml
import argparse
from typing import List, Optional, Dict
from datetime import datetime
import re
import shutil

# Asegurar que podemos importar módulos locales
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.company import Company, CompetitorAnalysis
from scrapers.google_maps import GoogleMapsScraper
from scrapers.eleconomista import ElEconomistaScraper
from scoring.competitor_score import CompetitorScorer
from export.excel_export import ExcelExporter

OUTPUT_DIR = "output_excel"  # Carpeta donde se guardarán los Excel


class CompetitorAnalyzer:
    def __init__(self, config_path: str = "config.yaml"):
        # Cargar configuración con manejo de errores
        if not os.path.exists(config_path):
            print(f"⚠️  Archivo {config_path} no encontrado, usando configuración por defecto")
            self.config = self._get_default_config()
        else:
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                print(f"✅ Configuración cargada desde {config_path}")
            except Exception as e:
                print(f"⚠️  Error cargando {config_path}: {e}")
                self.config = self._get_default_config()
        
        self.google_scraper = GoogleMapsScraper(self.config)
        self.economista_scraper = ElEconomistaScraper(self.config)
        self.scorer = CompetitorScorer(self.config)
        self.exporter = ExcelExporter(self.config)
    
    def _get_default_config(self) -> Dict:
        """Configuración por defecto"""
        return {
            'scraping': {
                'timeout': 30,
                'max_retries': 3,
                'delay_between_requests': 2,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            'scoring': {
                'weights': {
                    'geographic_proximity': 0.35,
                    'relative_size': 0.35,
                    'licenses_won_24m': 0.20,
                    'google_reviews_score': 0.10
                },
                'size_multiplier': {'min': 3, 'max': 20},
                'geographic_priority': ['municipio', 'area_metropolitana', 'provincia', 'nacional']
            },
            'export': {'excel_format': 'xlsx', 'include_notes': True}
        }
    
    def analyze(self, company_name: str, cnae: str, province: str, city: str = None,
                employees: int = None, revenue: float = None) -> CompetitorAnalysis:
        """
        Analiza competidores para una empresa
        
        Args:
            company_name: Nombre de la empresa lead
            cnae: Código CNAE
            province: Provincia
            city: Ciudad (opcional)
            employees: Número de empleados (opcional)
            revenue: Facturación en M€ (opcional)
        """
        print(f"\n🔍 Analizando competidores para: {company_name}")
        print(f"   CNAE: {cnae} | Provincia: {province} | Ciudad: {city or 'No especificada'}")
        
        # Crear empresa lead
        lead = Company(
            name=company_name,
            cnae=cnae,
            city=city or "",
            province=province,
            employees=employees,
            revenue=revenue
        )
        
        # Buscar competidores
        competitors = []
        
        # 1. Buscar en Google Maps (competidores locales)
        print("\n📍 Buscando en Google Maps...")
        if city:
            try:
                local_comps = self.google_scraper.search_companies(
                    sector=self._get_sector_from_cnae(cnae),
                    city=city,
                    limit=10
                )
                competitors.extend(local_comps)
                print(f"   ✅ Encontrados {len(local_comps)} competidores locales")
            except Exception as e:
                print(f"   ⚠️  Error en Google Maps: {e}")
        
        # 2. Buscar en El Economista (competidores nacionales por CNAE)
        print("\n📊 Buscando en El Economista...")
        try:
            national_comps = self.economista_scraper.search_by_cnae(
                cnae=cnae,
                province=province if not city else None,
                limit=15
            )
            competitors.extend(national_comps)
            print(f"   ✅ Encontrados {len(national_comps)} competidores nacionales")
        except Exception as e:
            print(f"   ⚠️  Error en El Economista: {e}")
        
        # Si no hay competidores, generar datos de ejemplo para demostración
        if not competitors:
            print("\n⚠️  No se encontraron competidores reales. Generando datos de ejemplo...")
            competitors = self._generate_demo_companies(cnae, province, city)
        
        # Eliminar duplicados por nombre
        unique_comps = {}
        for comp in competitors:
            if comp.name not in unique_comps:
                unique_comps[comp.name] = comp
        competitors = list(unique_comps.values())
        
        print(f"\n📈 Total competidores únicos: {len(competitors)}")
        
        # Rankear competidores
        print("\n🏆 Calculando scores y ranking...")
        ranked = self.scorer.rank_competitors(lead, competitors)
        
        # Obtener top competidores
        result = self.scorer.get_top_competitors(lead, competitors, top_n=3, secondary_n=2)
        
        print(f"\n✨ Top 3 competidores:")
        for i, comp in enumerate(result['top'], 1):
            print(f"   {i}. {comp.name} (Score: {comp.total_score:.4f})")
        
        if result['secondary']:
            print(f"\n📋 Competidores secundarios:")
            for i, comp in enumerate(result['secondary'], 1):
                print(f"   {i}. {comp.name} (Score: {comp.total_score:.4f})")
        
        return CompetitorAnalysis(
            lead_company=lead,
            competitors=competitors,
            top_competitors=result['top'],
            secondary_competitors=result['secondary']
        )
    
    def _generate_demo_companies(self, cnae: str, province: str, city: str = None) -> List[Company]:
        """Genera datos de ejemplo para demostración"""
        demo_companies = [
            Company(
                name=f"Grupo {province} Solutions",
                cnae=cnae,
                city=city or province,
                province=province,
                employees=250,
                revenue=25.5,
                google_reviews=450,
                licenses_won_24m=35,
                phone="+34 900 123 456",
                website=f"www.grupo{province.lower()}.com",
                address=f"Calle Principal 1, {city or province}"
            ),
            Company(
                name=f"Tecnología {province}",
                cnae=cnae,
                city=city or province,
                province=province,
                employees=120,
                revenue=12.3,
                google_reviews=230,
                licenses_won_24m=18,
                phone="+34 900 123 457",
                website=f"www.tecnologia{province.lower()}.com"
            ),
            Company(
                name=f"Industrias del {province}",
                cnae=cnae,
                city=city or province,
                province=province,
                employees=80,
                revenue=8.7,
                google_reviews=120,
                licenses_won_24m=9
            ),
            Company(
                name="Nacional de Servicios SL",
                cnae=cnae,
                city="Madrid",
                province="Madrid",
                employees=500,
                revenue=52.0,
                google_reviews=890,
                licenses_won_24m=67
            ),
            Company(
                name="Innovación Empresarial SA",
                cnae=cnae,
                city="Barcelona",
                province="Barcelona",
                employees=320,
                revenue=34.2,
                google_reviews=560,
                licenses_won_24m=42
            )
        ]
        return demo_companies[:5]
    
    def export_results(self, analysis: CompetitorAnalysis, filename: str = None):
        """Exporta resultados a Excel"""
        if not filename:
            safe_name = analysis.lead_company.name.replace(' ', '_').replace('/', '_')
            filename = f"competitor_analysis_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        result_dict = {
            'top': analysis.top_competitors,
            'secondary': analysis.secondary_competitors
        }
        
        self.exporter.export_to_excel(analysis.lead_company, result_dict, filename)
        print(f"\n✅ Resultados exportados a: {filename}")
        return filename
    
    def _get_sector_from_cnae(self, cnae: str) -> str:
        """Convierte CNAE a término de búsqueda legible"""
        # Mapeo básico de CNAE a sectores comunes
        sector_map = {
            '4662': 'venta mayorista metales',
            '6201': 'programación informática',
            '6202': 'consultoría informática',
            '7112': 'ingeniería',
            '4121': 'construcción edificios',
            '5610': 'restaurantes',
            '4630': 'comercio alimentación',
            '7022': 'consultoría gestión empresarial',
        }
        return sector_map.get(cnae, f'empresas sector {cnae}')
    
    def cleanup(self):
        """Limpia recursos"""
        try:
            self.google_scraper.close()
        except:
            pass



def move_to_output_folder(source_file: str) -> str:
    """Mueve el archivo generado a la carpeta output_excel"""
    ensure_output_dir()
    
    # Obtener solo el nombre del archivo
    filename = os.path.basename(source_file)
    
    # Ruta destino
    dest_file = os.path.join(OUTPUT_DIR, filename)
    
    # Si el archivo ya existe en destino, añadir timestamp
    if os.path.exists(dest_file):
        name, ext = os.path.splitext(filename)
        timestamp = datetime.now().strftime('%H%M%S')
        filename = f"{name}_{timestamp}{ext}"
        dest_file = os.path.join(OUTPUT_DIR, filename)
    
    # Mover el archivo
    try:
        shutil.move(source_file, dest_file)
        print(f"📁 Archivo guardado en: {dest_file}")
        return dest_file
    except Exception as e:
        print(f"⚠️  Error al mover archivo: {e}")
        print(f"   Archivo guardado en: {source_file}")
        return source_file

def main():
    parser = argparse.ArgumentParser(description='Competitor Analyzer - Análisis de competidores para PYMES')
    parser.add_argument('--company', required=True, help='Nombre de la empresa')
    parser.add_argument('--cnae', required=True, help='Código CNAE')
    parser.add_argument('--province', required=True, help='Provincia')
    parser.add_argument('--city', help='Ciudad (opcional)')
    parser.add_argument('--employees', type=int, help='Número de empleados (opcional)')
    parser.add_argument('--revenue', type=float, help='Facturación en M€ (opcional)')
    parser.add_argument('--output', help='Archivo de salida Excel')
    parser.add_argument('--config', default='config.yaml', help='Archivo de configuración')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🚀 COMPETITOR ANALYZER - MVP")
    print("=" * 60)
    
    analyzer = CompetitorAnalyzer(config_path=args.config)
    
    try:
        analysis = analyzer.analyze(
            company_name=args.company,
            cnae=args.cnae,
            province=args.province,
            city=args.city,
            employees=args.employees,
            revenue=args.revenue
        )
        
        output_file = analyzer.export_results(analysis, args.output)
        
        print("\n" + "=" * 60)
        print(f"✅ Análisis completado exitosamente!")
        print(f"📁 Archivo generado: {output_file}")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Proceso interrumpido por el usuario")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        analyzer.cleanup()

if __name__ == "__main__":
    main()
