import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
import os
import sys

# -----------------------------
# NORMALIZACIÓN
# -----------------------------
def normalize_text(value):
    if not value or not isinstance(value, str):
        return ""
    value = value.strip().lower()
    blacklist = [
        "no contesta", "no disponible", "na", "n/a",
        "ocupado", "llamar", "no hay interes", "no hay interés",
        "no es lo que buscamos"
    ]
    for b in blacklist:
        if b in value:
            return ""
    return value.strip()

# -----------------------------
# VALIDADORES
# -----------------------------
def is_valid_email(email):
    if not email or not isinstance(email, str):
        return False

    email = email.strip().lower()

    if any(x in email for x in ["no@", "example", "test", "fake"]):
        return False

    if "." not in email.split("@")[-1]:
        return False

    return re.match(
        r"^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$",
        email
    )

def clean_phone(phone):
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("34") and len(digits) == 11:
        digits = digits[2:]
    return digits

def is_valid_phone(phone):
    if not phone:
        return False
    digits = clean_phone(phone)
    return len(digits) == 9 and digits[0] in "6789"

# -----------------------------
# SCRAPING WEB OFICIAL
# -----------------------------
def scrape_website_contacts(base_url):
    result = {"email": None, "phone": None}

    try:
        urls = [base_url]
        for suffix in ["/contacto", "/contact", "/aviso-legal"]:
            urls.append(urljoin(base_url, suffix))

        headers = {"User-Agent": "Mozilla/5.0"}

        for url in urls:
            r = requests.get(url, timeout=10, headers=headers)
            if r.status_code != 200:
                continue

            soup = BeautifulSoup(r.text, "html.parser")

            # 1️⃣ mailto / tel
            for a in soup.find_all("a", href=True):
                href = a["href"]

                if href.startswith("mailto:") and not result["email"]:
                    email = href.replace("mailto:", "").split("?")[0]
                    if is_valid_email(email):
                        result["email"] = email

                if href.startswith("tel:") and not result["phone"]:
                    phone = href.replace("tel:", "")
                    if is_valid_phone(phone):
                        result["phone"] = clean_phone(phone)

            # 2️⃣ texto plano
            text = soup.get_text(" ")

            if not result["email"]:
                emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text)
                for e in emails:
                    if is_valid_email(e):
                        result["email"] = e
                        break

            if not result["phone"]:
                phones = re.findall(r"\+?\d[\d\s\-]{8,}", text)
                for p in phones:
                    if is_valid_phone(p):
                        result["phone"] = clean_phone(p)
                        break

            if result["email"] or result["phone"]:
                break

    except Exception:
        pass

    return result

# -----------------------------
# MOTOR PRINCIPAL
# -----------------------------
def enrich_excel(input_file, output_file):
    df = pd.read_excel(input_file)
    df = df.fillna("")

    if "enrichment_log" not in df.columns:
        df["enrichment_log"] = ""

    for idx, row in df.iterrows():
        web = row.get("web", "").strip()
        email_raw = normalize_text(row.get("email", ""))
        telefono_raw = normalize_text(row.get("telefono", ""))

        needs_email = not is_valid_email(email_raw)
        needs_phone = not is_valid_phone(telefono_raw)

        if not web or not (needs_email or needs_phone):
            continue

        print(f"🔍 Scrapeando web: {web}")

        data = scrape_website_contacts(web)

        if needs_email and data["email"]:
            df.at[idx, "email"] = data["email"]
        elif needs_email:
            df.at[idx, "enrichment_log"] += "Email no encontrado; "

        if needs_phone and data["phone"]:
            df.at[idx, "telefono"] = data["phone"]
        elif needs_phone:
            df.at[idx, "enrichment_log"] += "Teléfono no encontrado; "

    df.to_excel(output_file, index=False)
    print(f"\n✅ Excel enriquecido guardado en: {output_file}")

# -----------------------------
# EJECUCIÓN CLI
# -----------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("❌ Uso:")
        print('   python3 enrich_excel.py "entrada.xlsx" ["salida.xlsx"]')
        sys.exit(1)

    input_file = sys.argv[1]

    if len(sys.argv) >= 3:
        output_file = sys.argv[2]
    else:
        base_name, _ = os.path.splitext(input_file)
        date_str = datetime.now().strftime("%Y%m%d")
        output_file = f"{base_name}_{date_str}_enriched.xlsx"

    enrich_excel(input_file, output_file)
