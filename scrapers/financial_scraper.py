"""
Scraper para datos financieros de empresas
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential

class FinancialScraper:
    """Scraper para datos financieros de empresas"""
    
    def __init__(self, config):
        self.config = config
        self.headers = {'User-Agent': config['scraping']['user_agent']}
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_financial_data(self, company_name: str, cnae: str = None) -> Dict:
        """
        Busca datos financieros (facturación, empleados, etc.)
        """
        result = {
            'revenue': None,  # en millones
            'employees': None,
            'profit': None,
            'growth_rate': None,
            'debt': None
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
                for row in rows:
                    if company_name.lower() in row.get_text().lower():
                        cells = row.find_all('td')
                        if len(cells) >= 4:
                            # Extraer facturación
                            revenue_text = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                            revenue = self._parse_revenue(revenue_text)
                            if revenue:
                                result['revenue'] = revenue
                            
                            # Extraer empleados
                            employees_text = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                            employees = self._parse_employees(employees_text)
                            if employees:
                                result['employees'] = employees
                        break
            
            # Si no encontramos, buscar en Google
            if not result['revenue'] and not result['employees']:
                query = f"{company_name} facturación empleados {cnae or ''}"
                search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                
                response = requests.get(search_url, headers=self.headers, timeout=15)
                response.raise_for_status()
                
                text = response.text
                
                # Buscar patrones
                revenue_pattern = r'factura[ció]n\s*(?:anual\s*)?(?:de\s*)?(\d+(?:\.\d+)?)\s*(?:millones|M€|M)'
                revenue_match = re.search(revenue_pattern, text, re.I)
                if revenue_match:
                    result['revenue'] = float(revenue_match.group(1))
                
                employees_pattern = r'(\d+(?:\.\d+)?)\s*(?:empleados|trabajadores)'
                employees_match = re.search(employees_pattern, text, re.I)
                if employees_match:
                    result['employees'] = int(float(employees_match.group(1)))
            
            return result
            
        except Exception as e:
            print(f"Error buscando datos financieros para {company_name}: {e}")
            return result
    
    def _parse_revenue(self, text: str) -> Optional[float]:
        """Parsea texto de facturación a número"""
        # Limpiar texto
        text = text.replace('M€', '').replace('€', '').replace(',', '').strip()
        
        # Buscar número
        match = re.search(r'(\d+(?:\.\d+)?)', text)
        if match:
            return float(match.group(1))
        return None
    
    def _parse_employees(self, text: str) -> Optional[int]:
        """Parsea texto de empleados a número"""
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))
        return None


class BusinessRegistryScraper:
    """Scraper del Registro Mercantil"""
    
    def __init__(self, config):
        self.config = config
        self.headers = {'User-Agent': config['scraping']['user_agent']}
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_registry_info(self, company_name: str) -> Dict:
        """
        Busca información del Registro Mercantil
        """
        result = {
            'cif': None,
            'founding_date': None,
            'legal_form': None,
            'board_members': []
        }
        
        try:
            # Buscar en InfoCif
            search_url = f"https://www.infocif.es/buscar?q={company_name.replace(' ', '+')}"
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Buscar CIF
            cif_match = re.search(r'[A-Z]\d{8}', soup.get_text())
            if cif_match:
                result['cif'] = cif_match.group(0)
            
            # Buscar fecha de fundación
            date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', soup.get_text())
            if date_match:
                result['founding_date'] = date_match.group(1)
            
            return result
            
        except Exception as e:
            print(f"Error buscando registro para {company_name}: {e}")
            return result
