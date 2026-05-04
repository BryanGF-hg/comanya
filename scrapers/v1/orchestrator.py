from sources.search_bing import search_company
from enrich.web_official import enrich_from_web

def scrape_company(name):
    data = {"name": name}

    # 1. Buscar web
    urls = search_company(name)
    if urls:
        data["web"] = urls[0]

    # 2. Enriquecer
    if data.get("web"):
        data.update(enrich_from_web(data["web"]))

    return data
