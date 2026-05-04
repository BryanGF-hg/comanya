# run.py
from sources.empresascif import search_empresa
from sources.google_basic import search_google_contact
from enrich.social import scrape_social
from enrich.licitaciones import scrape_licitaciones
import sys, os

sys.path.append(os.path.dirname(__file__))

def scrape_company(company_name: str) -> dict:
    data = {
        "name": company_name
    }

    # 1. Fuente principal (rápida)
    base = search_empresa(company_name)
    data.update(base)


    # 2. Fallback si falta info crítica
    if not data.get("phone") and not data.get("email"):
        fallback = search_google_contact(company_name)
        data.update(fallback)


    # 3. Redes sociales
    social = scrape_social(company_name, data.get("website"))
    data.update(social)

    # 4. Licitaciones
    lic = scrape_licitaciones(company_name)
    data["licitaciones"] = lic

    return data


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python run.py \"Empresa SL\"")
        sys.exit(1)

    company = sys.argv[1]
    result = scrape_company(company)

    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
