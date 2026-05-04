# puente hacia scrapers v1
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPERS_V1 = os.path.join(BASE_DIR, "scrapers", "v1")
sys.path.append(SCRAPERS_V1)

from run import scrape_company


def run_scraper(company, cnae, provincia, empleados=None, facturacion=None):
    """
    Ejecuta el scraper v1 y devuelve datos normalizados
    SOLO con campos válidos para MySQL
    """
    scraped = scrape_company(company)

    return {
        "empresa": company,
        "cnae": cnae,
        "provincia": provincia,
        "empleados": empleados,
        "facturacion": facturacion,
        "archivo_excel": None,  # se rellena después
    }
