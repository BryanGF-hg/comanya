#!/usr/bin/env python3
"""
enrichment_avanzado.py - Motor de scraping multi‑fuente para enriquecer leads
Versión basada en técnicas de Radar CRM v0.0.4
"""

import re
import time
import random
import threading
import json
import os
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse, quote_plus, unquote

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup

# ──────────────────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

# Dominios excluidos (directorios, redes sociales, etc.)
EXCLUDED_DOMAINS = {
    "google.com", "bing.com", "duckduckgo.com", "yahoo.com", "yandex.com",
    "facebook.com", "twitter.com", "instagram.com", "linkedin.com", "youtube.com",
    "wikipedia.org", "amazon.es", "amazon.com", "ebay.es", "milanuncios.com",
    "eleconomista.es", "ranking-empresas.eleconomista.es", "expansion.com",
    "einforma.com", "infoempresa.com", "axesor.es", "infocif.es", "empresascif.com",
    "cnae.com.es", "ine.es", "boe.es", "borme.es", "camara.es", "paginasamarillas.es",
}

# Patrones de extracción
RE_TEL = re.compile(r"(?<!\d)(?:\+34[\s.\-]?)?[6789]\d{2}[\s.\-]?\d{3}[\s.\-]?\d{3}(?!\d)")
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
RE_WEB = re.compile(r"https?://(?:www\.)?([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})")

# Control de ritmo global
_RATE_LOCK = threading.Lock()
_RATE_LAST = 0.0
_RATE_PENALTY = 0.0

def _safe_str(value):
    """Convierte cualquier valor a string de forma segura, manejando NaN y None"""
    if value is None:
        return ""
    if isinstance(value, float):
        if np.isnan(value):
            return ""
        return str(int(value)) if value.is_integer() else str(value)
    if isinstance(value, (int, bool)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()

def _throttle(min_delay=1.2):
    global _RATE_LAST, _RATE_PENALTY
    with _RATE_LOCK:
        now = time.time()
        wait = max(0.0, _RATE_LAST + min_delay + _RATE_PENALTY - now)
        if wait > 0:
            time.sleep(wait)
        _RATE_LAST = time.time()
        _RATE_PENALTY = max(0.0, _RATE_PENALTY - 0.05)

def _register_block():
    global _RATE_PENALTY
    with _RATE_LOCK:
        _RATE_PENALTY += 0.8

def _session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": random.choice(DEFAULT_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "DNT": "1",
        "Connection": "keep-alive",
    })
    return s

def _get(url, timeout=12, retries=2):
    for attempt in range(retries + 1):
        try:
            _throttle()
            resp = _session().get(url, timeout=timeout, allow_redirects=True)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code in (429, 403, 503):
                _register_block()
                if attempt < retries:
                    time.sleep(2 * (attempt + 1))
                    continue
        except Exception:
            if attempt < retries:
                time.sleep(1)
                continue
    return None

# ──────────────────────────────────────────────────────────────────────────────
# NORMALIZACIÓN Y VALIDACIÓN
# ──────────────────────────────────────────────────────────────────────────────
def clean_phone(phone):
    if not phone:
        return None
    phone_str = _safe_str(phone)
    digits = re.sub(r"\D", "", phone_str)
    if digits.startswith("34") and len(digits) == 11:
        digits = digits[2:]
    if len(digits) == 9 and digits[0] in "6789":
        return digits
    return None

def normalize_text(value):
    if value is None:
        return ""
    value_str = _safe_str(value)
    return value_str.strip().lower()

def is_valid_email(email):
    if not email:
        return False
    email_str = _safe_str(email).strip().lower()
    if any(x in email_str for x in ["no@", "example", "test", "fake"]):
        return False
    if "." not in email_str.split("@")[-1]:
        return False
    return bool(re.match(r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$", email_str))

def is_valid_phone(phone):
    return clean_phone(phone) is not None

# ──────────────────────────────────────────────────────────────────────────────
# BUSCADORES WEB (Bing, DuckDuckGo)
# ──────────────────────────────────────────────────────────────────────────────
def _bing_unwrap_url(href):
    if not href:
        return ""
    href_str = _safe_str(href)
    if "bing.com/ck" in href_str and "&u=a1" in href_str:
        try:
            import base64
            u = href_str.split("&u=a1")[1].split("&")[0]
            pad = "=" * ((4 - len(u) % 4) % 4)
            dec = base64.b64decode(u + pad).decode("utf-8", errors="ignore")
            if dec.startswith("http"):
                return dec
        except Exception:
            pass
    return href_str

def bing_search(query, count=10):
    """Busca en Bing y devuelve lista de {title, url, snippet}"""
    query_str = _safe_str(query)
    url = f"https://www.bing.com/search?q={quote_plus(query_str)}&setlang=es&count={count}"
    html = _get(url, timeout=10)
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    results = []
    for box in soup.select("li.b_algo"):
        a = box.select_one("h2 a")
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        href = _bing_unwrap_url(a.get("href", ""))
        snippet_el = box.select_one(".b_caption p") or box.select_one("p")
        snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
        if href and href.startswith("http"):
            results.append({"title": title, "url": href, "snippet": snippet})
    return results

def duckduckgo_search(query):
    """Busca en DuckDuckGo HTML (post)"""
    query_str = _safe_str(query)
    url = "https://html.duckduckgo.com/html/"
    data = {"q": query_str}
    headers = {"User-Agent": random.choice(DEFAULT_USER_AGENTS)}
    try:
        resp = requests.post(url, data=data, headers=headers, timeout=10)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "lxml")
        results = []
        for box in soup.select(".result"):
            a = box.select_one(".result__a") or box.find("a", href=True)
            if not a:
                continue
            title = a.get_text(" ", strip=True)
            href = a.get("href", "")
            if href.startswith("//"):
                href = "https:" + href
            snippet_el = box.select_one(".result__snippet")
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
            results.append({"title": title, "url": href, "snippet": snippet})
        return results
    except Exception:
        return []

# ──────────────────────────────────────────────────────────────────────────────
# SCRAPING DE WEB OFICIAL
# ──────────────────────────────────────────────────────────────────────────────
def scrape_website_contacts(base_url):
    """Extrae teléfono, email, web (ya la tenemos), dirección, gerente"""
    result = {"email": None, "phone": None, "address": None, "manager": None}
    if not base_url:
        return result
    base_url_str = _safe_str(base_url)
    if not base_url_str.startswith("http"):
        base_url_str = "https://" + base_url_str
    urls_to_try = [base_url_str]
    for suffix in ["/contacto", "/contact", "/aviso-legal", "/quienes-somos", "/empresa"]:
        urls_to_try.append(urljoin(base_url_str, suffix))

    for url in urls_to_try:
        html = _get(url, timeout=8)
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)

        # mailto / tel
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("mailto:") and not result["email"]:
                mail = href.replace("mailto:", "").split("?")[0]
                if is_valid_email(mail):
                    result["email"] = mail
            if href.startswith("tel:") and not result["phone"]:
                ph = clean_phone(href.replace("tel:", ""))
                if ph:
                    result["phone"] = ph

        # emails en texto
        if not result["email"]:
            emails = RE_EMAIL.findall(text)
            for e in emails:
                if is_valid_email(e):
                    result["email"] = e
                    break

        # teléfonos en texto
        if not result["phone"]:
            phones = RE_TEL.findall(text)
            for p in phones:
                ph = clean_phone(p)
                if ph:
                    result["phone"] = ph
                    break

        # dirección (patrón español)
        if not result["address"]:
            addr_match = re.search(
                r"(?:C/|Calle|Avda|Avenida|Plaza|Polígono|Paseo|Carretera)[\s\w,ºª\.\d]{10,80}",
                text, re.I)
            if addr_match:
                result["address"] = addr_match.group(0).strip()[:250]

        # gerente (patrón nombre)
        if not result["manager"]:
            mgr_match = re.search(
                r"(?:Administrador|Gerente|Director|CEO|Presidente)[:\s]+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})",
                text, re.I)
            if mgr_match:
                cand = mgr_match.group(1).strip()
                if len(cand.split()) >= 2:
                    result["manager"] = cand

        if result["email"] and result["phone"]:
            break
    return result

# ──────────────────────────────────────────────────────────────────────────────
# SCRAPING EMPRESASCIF
# ──────────────────────────────────────────────────────────────────────────────
def _empresascif_abs(href):
    if not href:
        return ""
    href_str = _safe_str(href)
    if href_str.startswith("http"):
        return href_str
    if href_str.startswith("//"):
        return "https:" + href_str
    return "https://www.empresascif.com" + href_str

def search_empresascif_company_urls(company_name, province=""):
    """
    Busca en empresascif.com usando Bing/DDG y devuelve URLs de fichas de empresa
    """
    candidates = []
    company_name_str = _safe_str(company_name)
    province_str = _safe_str(province)
    queries = [
        f'"{company_name_str}" site:empresascif.com/empresa',
        f'"{company_name_str}" {province_str} CIF site:empresascif.com',
    ]
    for q in queries:
        items = bing_search(q, count=5)
        if not items:
            items = duckduckgo_search(q)
        for it in items:
            url = it.get("url", "")
            if "/empresa/" in url and "empresascif.com" in url:
                candidates.append(url)
        if candidates:
            break
    return list(dict.fromkeys(candidates))

def parse_empresascif_page(url, target_cnae=None):
    """Extrae datos de una ficha de empresascif"""
    if not url:
        return None
    url_str = _safe_str(url)
    html = _get(url_str, timeout=8)
    if not html:
        return None
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)

    # Nombre (h1)
    nombre = ""
    h1 = soup.find("h1")
    if h1:
        nombre = h1.get_text(" ", strip=True)

    # CNAE
    cnae = None
    m_cnae = re.search(r"CNAE[:\s]*(\d{3,4})", text, re.I)
    if m_cnae:
        cnae = m_cnae.group(1)
        if target_cnae and cnae != str(target_cnae):
            return None

    # Teléfono
    phone = None
    tel_match = RE_TEL.search(text)
    if tel_match:
        phone = clean_phone(tel_match.group(0))

    # Email
    email = None
    email_match = RE_EMAIL.search(text)
    if email_match:
        email = email_match.group(0)
        if is_valid_email(email):
            email = email

    # Dirección
    address = None
    addr_match = re.search(r"(?:Domicilio|Dirección)[:\s]+([A-ZÁÉÍÓÚÑ][^\n]{10,80})", text, re.I)
    if addr_match:
        address = addr_match.group(1).strip()

    # Gerente/Administrador
    manager = None
    mgr_match = re.search(r"Administrador(?:a)?[:\s]+([A-Z][a-záéíóúñ]+(?:\s+[A-Z][a-záéíóúñ]+){1,3})", text, re.I)
    if mgr_match:
        manager = mgr_match.group(1).strip()

    return {
        "nombre": nombre,
        "cnae": cnae,
        "telefono": phone,
        "email": email,
        "direccion": address,
        "gerente": manager,
        "web": None,
        "url": url_str,
    }

# ──────────────────────────────────────────────────────────────────────────────
# BÚSQUEDA DE WEB OFICIAL VÍA CLEARBIT / HEURÍSTICA
# ──────────────────────────────────────────────────────────────────────────────
def slugify_company_name(name):
    """Convierte nombre de empresa a slug para dominios"""
    if not name:
        return ""
    name_str = _safe_str(name)
    name_str = re.sub(r"\s+(S\.?A\.?U?|S\.?L\.?U?|S\.?L\.?P|GROUP|GRUPO|SA|SL)$", "", name_str, flags=re.I)
    name_str = name_str.lower()
    name_str = re.sub(r"[^a-z0-9\s-]", "", name_str)
    name_str = re.sub(r"\s+", "-", name_str).strip("-")
    return name_str

def guess_website(company_name):
    """Intenta encontrar web oficial por heurística de dominio"""
    slug = slugify_company_name(company_name)
    if not slug or len(slug) < 3:
        return None
    for tld in [".es", ".com"]:
        url = f"https://www.{slug}{tld}"
        try:
            r = requests.get(url, timeout=3, allow_redirects=True)
            if r.status_code == 200:
                if "parked" not in r.text.lower() and "domain" not in r.text.lower():
                    return r.url
        except Exception:
            continue
    return None

def find_website_via_search(company_name, province=""):
    """Usa Bing para encontrar la web oficial"""
    company_name_str = _safe_str(company_name)
    province_str = _safe_str(province)
    queries = [f'"{company_name_str}" {province_str} web oficial', f'"{company_name_str}" {province_str} sitio web']
    for q in queries:
        results = bing_search(q, count=5)
        for r in results:
            url = r.get("url", "")
            dom = urlparse(url).netloc.replace("www.", "").lower()
            if dom not in EXCLUDED_DOMAINS and any(ext in url for ext in [".es", ".com", ".org"]):
                slug = slugify_company_name(company_name_str)
                if slug and slug in url.lower():
                    return url
    return None

# ──────────────────────────────────────────────────────────────────────────────
# ENRIQUECIMIENTO COMPLETO DE UN LEAD
# ──────────────────────────────────────────────────────────────────────────────
def enrich_single_lead(name, province="", current_web=None, current_email=None, current_phone=None):
    """
    Devuelve dict con todos los campos enriquecidos.
    Estrategia en cascada:
      1. Encontrar web oficial (si no se tiene)
      2. Scrapear web oficial
      3. Buscar en empresascif
      4. Buscar en Bing snippets (tel/email directos)
    """
    result = {
        "web": _safe_str(current_web) if current_web else None,
        "email": _safe_str(current_email) if current_email else None,
        "telefono": clean_phone(current_phone) if current_phone else None,
        "direccion": None,
        "gerente": None,
        "cnae": None,
    }

    name_str = _safe_str(name)
    province_str = _safe_str(province)

    if not name_str:
        return result

    # 1. Si no tenemos web, intentar adivinarla
    if not result["web"]:
        result["web"] = guess_website(name_str)
    if not result["web"] and province_str:
        result["web"] = find_website_via_search(name_str, province_str)
    if not result["web"]:
        result["web"] = find_website_via_search(name_str)

    # 2. Scrapear web oficial
    if result["web"]:
        web_data = scrape_website_contacts(result["web"])
        if web_data.get("email") and not result["email"]:
            result["email"] = web_data["email"]
        if web_data.get("phone") and not result["telefono"]:
            result["telefono"] = web_data["phone"]
        if web_data.get("address"):
            result["direccion"] = web_data["address"]
        if web_data.get("manager"):
            result["gerente"] = web_data["manager"]

    # 3. Buscar en empresascif
    if not result["telefono"] or not result["email"]:
        urls = search_empresascif_company_urls(name_str, province_str)
        for url in urls[:3]:
            data = parse_empresascif_page(url)
            if data:
                if data.get("telefono") and not result["telefono"]:
                    result["telefono"] = data["telefono"]
                if data.get("email") and not result["email"]:
                    result["email"] = data["email"]
                if data.get("direccion") and not result["direccion"]:
                    result["direccion"] = data["direccion"]
                if data.get("gerente") and not result["gerente"]:
                    result["gerente"] = data["gerente"]
                if data.get("cnae") and not result["cnae"]:
                    result["cnae"] = data["cnae"]
                if result["telefono"] and result["email"]:
                    break
            time.sleep(0.5)

    # 4. Bing snippets (si aún faltan datos)
    if not result["telefono"] or not result["email"]:
        q = f'"{name_str}" {province_str} contacto telefono email'
        items = bing_search(q, count=8)
        texto = " ".join([it.get("snippet", "") for it in items])
        if not result["telefono"]:
            tel_match = RE_TEL.search(texto)
            if tel_match:
                result["telefono"] = clean_phone(tel_match.group(0))
        if not result["email"]:
            email_match = RE_EMAIL.search(texto)
            if email_match and is_valid_email(email_match.group(0)):
                result["email"] = email_match.group(0)

    # Limpiar valores vacíos
    for k in result:
        if not result[k]:
            result[k] = None

    return result

# ──────────────────────────────────────────────────────────────────────────────
# PROCESAMIENTO DE LOTES (EXCEL)
# ──────────────────────────────────────────────────────────────────────────────
def enrich_dataframe(df, max_workers=5, delay_between=0.5):
    """
    Enriquecer un DataFrame con columnas:
       nombre, provincia, web, email, telefono, direccion, gerente, cnae
    Devuelve DataFrame actualizado y un log.
    """
    # Asegurar columnas necesarias
    required_cols = ["nombre", "provincia", "web", "email", "telefono", "direccion", "gerente", "cnae", "enrichment_log"]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    # Convertir a lista de dicts para procesamiento, asegurando valores string
    leads = []
    for _, row in df.iterrows():
        lead_dict = {}
        for col in df.columns:
            lead_dict[col] = _safe_str(row[col]) if pd.notna(row[col]) else ""
        leads.append(lead_dict)

    enriched = []
    total = len(leads)

    # Semáforo para control de concurrencia y delay
    sem = threading.Semaphore(max_workers)

    def process_one(lead, idx):
        with sem:
            name = lead.get("nombre", "").strip()
            if not name:
                lead["enrichment_log"] = "Nombre vacío"
                return lead
            province = lead.get("provincia", "").strip()
            current_web = lead.get("web", "").strip() or None
            current_email = lead.get("email", "").strip() or None
            current_phone = lead.get("telefono", "").strip() or None

            print(f"[{idx+1}/{total}] Procesando: {name[:50]}...")
            
            try:
                enriched_data = enrich_single_lead(
                    name, province,
                    current_web=current_web,
                    current_email=current_email,
                    current_phone=current_phone
                )

                # Actualizar campos
                changes = []
                if enriched_data.get("web") and not current_web:
                    lead["web"] = enriched_data["web"]
                    changes.append("web encontrada")
                if enriched_data.get("email") and not current_email:
                    lead["email"] = enriched_data["email"]
                    changes.append("email encontrado")
                if enriched_data.get("telefono") and not current_phone:
                    lead["telefono"] = enriched_data["telefono"]
                    changes.append("teléfono encontrado")
                if enriched_data.get("direccion"):
                    lead["direccion"] = enriched_data["direccion"]
                if enriched_data.get("gerente"):
                    lead["gerente"] = enriched_data["gerente"]
                if enriched_data.get("cnae"):
                    lead["cnae"] = enriched_data["cnae"]
                
                lead["enrichment_log"] = "; ".join(changes) if changes else "sin cambios"
                
            except Exception as e:
                lead["enrichment_log"] = f"Error: {str(e)[:100]}"
                print(f"  ⚠️ Error en {name}: {str(e)[:80]}")
            
            # Delay entre empresas (respetar ritmo)
            time.sleep(delay_between)
            return lead

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_one, lead, i): i for i, lead in enumerate(leads)}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                enriched_lead = future.result()
                enriched.append(enriched_lead)
            except Exception as e:
                print(f"Error en lead {idx}: {e}")
                leads[idx]["enrichment_log"] = f"Error: {str(e)[:100]}"
                enriched.append(leads[idx])

    # Reordenar por índice original
    enriched.sort(key=lambda x: leads.index(x) if x in leads else 0)
    df_out = pd.DataFrame(enriched)
    return df_out

# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL CLI
# ──────────────────────────────────────────────────────────────────────────────
def enrich_excel_file(input_file, output_file=None, max_workers=5, delay=0.5):
    """Lee un Excel, enriquece y guarda."""
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"No se encuentra {input_file}")

    df = pd.read_excel(input_file)
    print(f"📊 Cargado {len(df)} registros de {input_file}")

    df_enriched = enrich_dataframe(df, max_workers=max_workers, delay_between=delay)

    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"

    df_enriched.to_excel(output_file, index=False)
    print(f"✅ Excel enriquecido guardado en: {output_file}")
    return output_file

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso:")
        print("   python enrichment_avanzado.py entrada.xlsx [salida.xlsx] [--workers 5] [--delay 0.5]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None

    # Parsear argumentos opcionales
    workers = 5
    delay = 0.5
    for i, arg in enumerate(sys.argv):
        if arg == "--workers" and i+1 < len(sys.argv):
            try:
                workers = int(sys.argv[i+1])
            except:
                pass
        if arg == "--delay" and i+1 < len(sys.argv):
            try:
                delay = float(sys.argv[i+1])
            except:
                pass

    enrich_excel_file(input_file, output_file, max_workers=workers, delay=delay)
