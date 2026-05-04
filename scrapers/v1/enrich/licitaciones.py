# enrich/licitaciones.py
import re
from core.http import get

def scrape_licitaciones(company: str) -> dict:
    query = f"{company} licitación adjudicado"
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"

    result = {
        "found": False,
        "count": 0,
        "last_amount": None
    }

    try:
        html = get(url)
        text = html.lower()

        if "licitación" in text or "adjudicado" in text:
            result["found"] = True

        count = re.search(r'(\d+)\s+licitaciones', text)
        if count:
            result["count"] = int(count.group(1))

        amount = re.search(r'(\d+(?:,\d+)?)\s*(m€|millones)', text)
        if amount:
            result["last_amount"] = amount.group(1)

    except Exception:
        pass

    return result
