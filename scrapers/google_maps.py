import time
import re
from typing import List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from tenacity import retry, stop_after_attempt, wait_exponential
from models.company import Company

class GoogleMapsScraper:
    def __init__(self, config):
        self.config = config
        self.driver = None
    
    def setup_driver(self):
        """Configura el driver de Chrome headless"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument(f"user-agent={self.config['scraping']['user_agent']}")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def search_companies(self, sector: str, city: str, limit: int = 10) -> List[Company]:
        """Busca empresas en Google Maps por sector y ciudad"""
        if not self.driver:
            self.setup_driver()
        
        query = f"{sector} {city} España"
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        
        self.driver.get(search_url)
        time.sleep(self.config['scraping']['delay_between_requests'])
        
        companies = []
        try:
            # Esperar a que carguen los resultados
            wait = WebDriverWait(self.driver, self.config['scraping']['timeout'])
            results = wait.until(EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div[role='article']")
            ))
            
            for i, result in enumerate(results[:limit]):
                try:
                    name_elem = result.find_element(By.CSS_SELECTOR, ".fontHeadlineSmall")
                    name = name_elem.text
                    
                    # Extraer reseñas
                    reviews_text = ""
                    try:
                        reviews_elem = result.find_element(By.CSS_SELECTOR, ".fontBodyMedium span[aria-label*='estrellas']")
                        reviews_text = reviews_elem.get_attribute('aria-label') or ""
                    except:
                        pass
                    
                    # Parsear reseñas
                    reviews_count = 0
                    rating = 0.0
                    if 'estrellas' in reviews_text:
                        import re
                        rating_match = re.search(r'(\d+,\d+|\d+)', reviews_text)
                        if rating_match:
                            rating = float(rating_match.group(1).replace(',', '.'))
                    
                    # Extraer dirección
                    address = ""
                    try:
                        address_elem = result.find_element(By.CSS_SELECTOR, ".W4Efsd:not(.fontBodyMedium)")
                        address = address_elem.text
                    except:
                        pass
                    
                    company = Company(
                        name=name,
                        cnae="",  # Se llenará después
                        city=city,
                        province="",  # Se llenará después
                        google_reviews=reviews_count,
                        google_rating=rating,
                        address=address,
                        municipality=city
                    )
                    companies.append(company)
                    
                except Exception as e:
                    print(f"Error extrayendo empresa: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error en búsqueda de Google Maps: {e}")
        
        return companies
    
    def close(self):
        if self.driver:
            self.driver.quit()
