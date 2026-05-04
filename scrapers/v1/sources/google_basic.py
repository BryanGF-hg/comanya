import re
from core.http import get

def search_google_contact(company: str) -> dict:
    data = {}
    url = f"https://www.google.com/search?q={company.replace(' ', '+')}+contacto"

    try:
        html = get(url)
    except Exception:
        return data

    phone = re.search(r'(\+34)?\s?\d{9}', html)
    if phone:
        data["phone"] = phone.group(0)

    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', html)
    if email:
        data["email"] = email.group(0)

    return data
