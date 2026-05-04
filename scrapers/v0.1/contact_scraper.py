"""
Scraper para buscar datos de contacto (teléfono, email, website)
de empresas españolas desde múltiples fuentes
"""

import re
import requests
from bs4 import BeautifulSoup
from typing import Optional, Dict
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib.parse import urljoin, urlparse

class ContactScraper:
    def __init__(self, config):
        self.config = config
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3',
        }
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_contact_info(self, company_name: str, province: str = None) -> Dict:
        """
        Busca información de contacto de una empresa
        Returns: dict con phone, email, website
        """
        result = {
            'phone': None,
            'email': None,
            'website': None,
            'address': None,
            'source': None
        }
        
        # 1. Buscar en Google (búsqueda simple)
        google_result = self._search_google(company_name, province)
        if google_result:
            result.update(google_result)
            result['source'] = 'Google'
        
        # 2. Buscar en Paginas Amarillas
        if not result['phone']:
            paginas_amarillas = self._search_paginas_amarillas(company_name, province)
            if paginas_amarillas:
                result.update(paginas_amarillas)
                result['source'] = 'Paginas Amarillas'
        
        # 3. Buscar en InfoEmpresa
        if not result['phone']:
            infoempresa = self._search_infoempresa(company_name)
            if infoempresa:
                result.update(infoempresa)
                result['source'] = 'InfoEmpresa'
        
        # 4. Buscar en LinkedIn (si no se encontró email)
        if not result['email']:
            linkedin = self._search_linkedin(company_name)
            if linkedin and linkedin.get('email'):
                result['email'] = linkedin['email']
                result['source'] = 'LinkedIn'
        
        return result
    
    def _search_google(self, company_name: str, province: str = None) -> Optional[Dict]:
        """Busca en Google usando búsqueda normal"""
        try:
            query = f"{company_name} {province or ''} contacto teléfono email".strip()
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            result = {}
            
            # Buscar teléfonos españoles
            phone_patterns = [
                r'(\+34\s*\d{3}\s*\d{3}\s*\d{3})',
                r'(\d{3}\s*\d{3}\s*\d{3})',
                r'(\d{9})',
                r'(\d{3}\.\d{3}\.\d{3})',
                r'(\d{3}-\d{3}-\d{3})'
            ]
            
            for pattern in phone_patterns:
                phones = re.findall(pattern, text)
                for phone in phones:
                    # Limpiar el teléfono
                    clean_phone = re.sub(r'[\s\.-]', '', phone)
                    if len(clean_phone) >= 9:
                        result['phone'] = f"+34 {clean_phone[:3]} {clean_phone[3:6]} {clean_phone[6:9]}"
                        break
                if result.get('phone'):
                    break
            
            # Buscar emails
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, text)
            if emails:
                result['email'] = emails[0]
            
            # Buscar website
            website_pattern = r'(https?://[^\s]+\.(?:es|com|org|net)[^\s]*)'
            websites = re.findall(website_pattern, text)
            if websites:
                result['website'] = websites[0]
            
            return result if result else None
            
        except Exception as e:
            print(f"Error en búsqueda Google para {company_name}: {e}")
            return None
    
    def _search_paginas_amarillas(self, company_name: str, province: str = None) -> Optional[Dict]:
        """Busca en Paginas Amarillas"""
        try:
            # Limpiar nombre para la URL
            clean_name = company_name.replace(' ', '-').lower()
            url = f"https://www.paginasamarillas.es/search/{clean_name}/all-ma/all-is/all-ci/all-ba/all-pu/all-nc/1"
            
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            result = {}
            
            # Buscar teléfono
            phone_elem = soup.find('span', class_=re.compile(r'phone', re.I))
            if phone_elem:
                phone_text = phone_elem.get_text(strip=True)
                phone_match = re.search(r'(\d{3}\s*\d{3}\s*\d{3})', phone_text)
                if phone_match:
                    phone = re.sub(r'\s', '', phone_match.group(1))
                    result['phone'] = f"+34 {phone[:3]} {phone[3:6]} {phone[6:9]}"
            
            # Buscar email
            email_elem = soup.find('a', href=re.compile(r'mailto:', re.I))
            if email_elem:
                email = email_elem.get('href', '').replace('mailto:', '')
                result['email'] = email
            
            # Buscar website
            web_elem = soup.find('a', href=re.compile(r'https?://', re.I), text=re.compile(r'www', re.I))
            if web_elem:
                result['website'] = web_elem.get('href')
            
            return result if result else None
            
        except Exception as e:
            print(f"Error en Paginas Amarillas para {company_name}: {e}")
            return None
    
    def _search_infoempresa(self, company_name: str) -> Optional[Dict]:
        """Busca en InfoEmpresa.es"""
        try:
            search_url = f"https://www.infoempresa.com/buscar?q={company_name.replace(' ', '+')}"
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            result = {}
            
            # Buscar en la página de resultados
            empresa_link = soup.find('a', href=re.compile(r'/empresa/'))
            if empresa_link:
                empresa_url = urljoin('https://www.infoempresa.com', empresa_link.get('href'))
                response2 = requests.get(empresa_url, headers=self.headers, timeout=15)
                soup2 = BeautifulSoup(response2.content, 'html.parser')
                
                # Extraer información
                text = soup2.get_text()
                
                # Teléfono
                phone_match = re.search(r'Tel[ée]fono:?\s*(\+?\d{1,3}[\s-]?\d{3}[\s-]?\d{3}[\s-]?\d{3})', text, re.I)
                if phone_match:
                    phone = re.sub(r'[\s-]', '', phone_match.group(1))
                    if len(phone) == 9:
                        result['phone'] = f"+34 {phone[:3]} {phone[3:6]} {phone[6:9]}"
                
                # Email
                email_match = re.search(r'Email:?\s*([\w\.-]+@[\w\.-]+\.\w+)', text, re.I)
                if email_match:
                    result['email'] = email_match.group(1)
                
                # Website
                web_match = re.search(r'Web:?\s*(https?://[^\s]+)', text, re.I)
                if web_match:
                    result['website'] = web_match.group(1)
            
            return result if result else None
            
        except Exception as e:
            print(f"Error en InfoEmpresa para {company_name}: {e}")
            return None
    
    def _search_linkedin(self, company_name: str) -> Optional[Dict]:
        """Busca en LinkedIn (búsqueda básica sin autenticación)"""
        try:
            search_url = f"https://www.google.com/search?q=linkedin+{company_name.replace(' ', '+')}+contacto"
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # Buscar emails en formato de LinkedIn
            # Nota: LinkedIn normalmente no muestra emails directamente
            email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
            emails = re.findall(email_pattern, text)
            
            return {'email': emails[0]} if emails else None
            
        except Exception as e:
            print(f"Error en LinkedIn para {company_name}: {e}")
            return None


class AddressScraper:
    """Scraper para direcciones y geolocalización"""
    
    def __init__(self, config):
        self.config = config
        self.headers = {'User-Agent': config['scraping']['user_agent']}
    
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=5))
    def search_address(self, company_name: str, city: str = None) -> Dict:
        """Busca dirección de la empresa"""
        result = {
            'address': None,
            'postal_code': None,
            'municipality': None,
            'coordinates': None
        }
        
        try:
            query = f"{company_name} {city or ''} dirección".strip()
            search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            
            response = requests.get(search_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            
            # Buscar dirección (patrón español)
            address_patterns = [
                r'(C/|Calle|Avda|Avenida|Plaza|Paseo)[\s\w,\.\d]+[\d]{5}[\s\w]+',
                r'(Polígono|Parque)[\s\w]+(nº|Nº|nro)[\s\d]+',
                r'(Ctra|Carretera)[\s\w]+(km|Km)[\s\d\.]+'
            ]
            
            for pattern in address_patterns:
                address_match = re.search(pattern, text, re.I)
                if address_match:
                    result['address'] = address_match.group(0)
                    break
            
            # Buscar código postal (5 dígitos)
            cp_match = re.search(r'\b(\d{5})\b', text)
            if cp_match:
                result['postal_code'] = cp_match.group(1)
            
            return result
            
        except Exception as e:
            print(f"Error buscando dirección para {company_name}: {e}")
            return result
