"""
Scraper para obtener detalles adicionales de competidores
(licitaciones, ranking, etc.)
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential

class CompetitorDetailsScraper:
    """Scraper para detalles de competidores"""
    
    def __init__(self, config):
        self.config = config
        self.headers = {'User-Agent': config['scraping']['user_agent']}
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_licitaciones(self, company_name: str, cnae: str = None) -> Dict:
        """
        Busca licitaciones ganadas por la empresa
        Returns: dict con número de licitaciones, años, etc.
        """
        result = {
            'licenses_won': 0,
            'licenses_last_24m': 0,
            'total_amount': 0,
            'last_contract': None
        }
        
        try:
            # Buscar en Plataforma de Contratación del Estado
            query = f"{company_name} licitación contratación pública"
            if cnae:
                query += f" {cnae}"
            
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # Buscar patrones de licitaciones
            # (simulado - en producción se usaría API del PLACSP)
            license_patterns = [
                r'(\d+)\s*licitaciones?\s*(?:ganadas?|adjudicadas?)',
                r'adjudicado\s*por\s*(\d+(?:\.\d+)?)\s*(?:millones|M€)',
                r'contrato\s*de\s*(\d+(?:\.\d+)?)\s*(?:millones|M€)'
            ]
            
            for pattern in license_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    if 'licitaciones' in pattern:
                        result['licenses_won'] = int(match.group(1))
                        result['licenses_last_24m'] = int(match.group(1)) // 2
                    break
            
            return result
            
        except Exception as e:
            print(f"Error buscando licitaciones para {company_name}: {e}")
            return result
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_ranking_info(self, company_name: str, cnae: str = None) -> Dict:
        """
        Busca información de ranking de la empresa
        Returns: dict con ranking, posición, etc.
        """
        result = {
            'ranking': None,
            'sector_position': None,
            'national_position': None
        }
        
        try:
            # Buscar en El Economista
            url = "https://ranking-empresas.eleconomista.es"
            if cnae:
                url += f"/ranking_empresas_nacional.html?qSectorNorm={cnae}"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar la empresa en la tabla
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for i, row in enumerate(rows, 1):
                    if company_name.lower() in row.get_text().lower():
                        result['ranking'] = i
                        result['sector_position'] = i
                        break
            
            return result
            
        except Exception as e:
            print(f"Error buscando ranking para {company_name}: {e}")
            return result


class ReviewScraper:
    """Scraper para reseñas y reputación online"""
    
    def __init__(self, config):
        self.config = config
        self.headers = {'User-Agent': config['scraping']['user_agent']}
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_reviews(self, company_name: str, city: str = None) -> Dict:
        """
        Busca reseñas en Google Maps y Trustpilot
        """
        result = {
            'google_reviews': 0,
            'google_rating': 0.0,
            'trustpilot_reviews': 0,
            'trustpilot_rating': 0.0,
            'total_score': 0
        }
        
        # Buscar en Google Maps (simulado)
        try:
            query = f"{company_name} {city or ''} reseñas".strip()
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # Patrones de reseñas
            review_patterns = [
                r'(\d+(?:,\d+)?)\s*(?:reseñas|opiniones)',
                r'Valoración:\s*(\d+(?:,\d+)?)\s*de\s*5',
                r'(\d+(?:\.\d+)?)\s*estrellas'
            ]
            
            for pattern in review_patterns:
                match = re.search(pattern, text, re.I)
                if match:
                    if 'reseñas' in pattern:
                        result['google_reviews'] = int(match.group(1).replace(',', ''))
                    elif 'Valoración' in pattern or 'estrellas' in pattern:
                        result['google_rating'] = float(match.group(1).replace(',', '.'))
                    break
            
            return result
            
        except Exception as e:
            print(f"Error buscando reseñas para {company_name}: {e}")
            return result
