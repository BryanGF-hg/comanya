# enrich/social.py
import re
from core.http import get

SOCIAL_PATTERNS = {
    "linkedin": r"https?://(www\.)?linkedin\.com/company/[\w-]+",
    "twitter": r"https?://(www\.)?(twitter|x)\.com/[\w-]+",
    "facebook": r"https?://(www\.)?facebook\.com/[\w.-]+",
    "instagram": r"https?://(www\.)?instagram\.com/[\w.-]+"
}

def scrape_social(company: str, website: str = None) -> dict:
    result = {}

    sources = []
    if website:
        sources.append(website)

    sources.append(f"https://www.google.com/search?q={company.replace(' ', '+')}+redes+sociales")

    for src in sources:
        try:
            html = get(src)
            for name, pattern in SOCIAL_PATTERNS.items():
                if name not in result:
                    m = re.search(pattern, html, re.I)
                    if m:
                        result[name] = m.group(0)
        except Exception:
            continue

    return result
