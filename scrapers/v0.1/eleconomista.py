import requests
import re
from bs4 import BeautifulSoup
from typing import List, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from models.company import Company

class ElEconomistaScraper:
    def __init__(self, config):
        self.config = config
        self.base_url = "https://ranking-empresas.eleconomista.es"
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_by_cnae(self, cnae: str, province: str = None, limit: int = 20) -> List[Company]:
        """Busca empresas por CNAE en El Economista"""
        url = f"{self.base_url}/ranking_empresas_nacional.html?qSectorNorm={cnae}"
        if province:
            url += f"&qProvincia={province}"
        
        headers = {'User-Agent': self.config['scraping']['user_agent']}
        response = requests.get(url, headers=headers, timeout=self.config['scraping']['timeout'])
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        companies = []
        
        # Buscar tabla de empresas
        table = soup.find('table', {'class': re.compile(r'.*ranking.*')})
        if not table:
            return companies
        
        rows = table.find_all('tr')[1:limit+1]  # Saltar header
        
        for row in rows:
            try:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    name = cols[0].get_text(strip=True)
                    
                    # Extraer datos financieros
                    revenue_text = cols[2].get_text(strip=True) if len(cols) > 2 else "0"
                    revenue = self._parse_euro_amount(revenue_text)
                    
                    employees_text = cols[3].get_text(strip=True) if len(cols) > 3 else "0"
                    employees = self._parse_number(employees_text)
                    
                    company = Company(
                        name=name,
                        cnae=cnae,
                        city="",
                        province=province or "",
                        revenue=revenue,
                        employees=employees,
                        source_url=url
                    )
                    companies.append(company)
                    
            except Exception as e:
                print(f"Error extrayendo empresa de El Economista: {e}")
                continue
        
        return companies
    
    def _parse_euro_amount(self, text: str) -> float:
        """Convierte texto como '1.234,56 M€' a float"""
        import re
        text = text.replace('M€', '').replace('€', '').strip()
        text = text.replace('.', '').replace(',', '.')
        match = re.search(r'[\d\.]+', text)
        if match:
            return float(match.group())
        return 0.0
    
    def _parse_number(self, text: str) -> int:
        """Convierte texto a número"""
        import re
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        return 0
