# sources/empresascif.py
import re
from bs4 import BeautifulSoup
from core.http import get

def search_empresa(name: str) -> dict:
    data = {}
    try:
      url = f"https://www.empresascif.es/buscar/{name.replace(' ', '-')}"
      html = get(url)
    except Exception as e:
      return data

    # Web
    web = soup.select_one("a[href^='http']")
    if web:
        data["website"] = web.get("href")

    # Teléfono
    soup = BeautifulSoup(html, "lxml")    
    text = soup.get_text(" ")
    phone = re.search(r'(\+34)?\s?\d{9}', text)
    if phone:
        data["phone"] = phone.group(0)

    # Email
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    if email:
        data["email"] = email.group(0)

    return data

