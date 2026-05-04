"""
Scraper para redes sociales de empresas
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

class SocialMediaScraper:
    """Scraper para links de redes sociales"""
    
    def __init__(self, config):
        self.config = config
        self.headers = {'User-Agent': config['scraping']['user_agent']}
        self.social_patterns = {
            'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|school)/[\w-]+',
            'twitter': r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[\w-]+',
            'facebook': r'(?:https?://)?(?:www\.)?facebook\.com/[\w\.-]+',
            'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/[\w\.-]+',
            'youtube': r'(?:https?://)?(?:www\.)?youtube\.com/(?:user|c|channel)/[\w-]+'
        }
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_social_media(self, company_name: str, website: str = None) -> Dict:
        """
        Busca perfiles de redes sociales de la empresa
        """
        result = {
            'linkedin': None,
            'twitter': None,
            'facebook': None,
            'instagram': None,
            'youtube': None
        }
        
        try:
            # Si tenemos website, buscar directamente ahí
            if website and website.startswith('http'):
                response = requests.get(website, headers=self.headers, timeout=15)
                response.raise_for_status()
                html = response.text
                
                for social, pattern in self.social_patterns.items():
                    match = re.search(pattern, html, re.I)
                    if match:
                        result[social] = match.group(0)
            
            # Si no, buscar en Google
            if not any(result.values()):
                query = f"{company_name} redes sociales linkedin twitter"
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                
                response = requests.get(search_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                text = soup.get_text()
                
                for social, pattern in self.social_patterns.items():
                    match = re.search(pattern, text, re.I)
                    if match:
                        result[social] = match.group(0)
            
            return result
            
        except Exception as e:
            print(f"Error buscando redes sociales para {company_name}: {e}")
            return result
    
    def extract_employee_count(self, linkedin_url: str) -> Optional[int]:
        """Extrae número de empleados de LinkedIn (simulado)"""
        # Nota: Esto requiere autenticación en LinkedIn en producción
        # Por ahora retorna un valor simulado basado en el nombre
        import random
        random.seed(linkedin_url)
        return random.randint(10, 500)
