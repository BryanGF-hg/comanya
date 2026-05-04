from bs4 import BeautifulSoup
from core.http import get

def search_company(name):
    url = f"https://www.bing.com/search?q={name.replace(' ', '+')}"
    html = get(url)
    soup = BeautifulSoup(html, "lxml")

    results = []
    for a in soup.select("li.b_algo h2 a"):
        href = a.get("href")
        if href:
            results.append(href)

    return results
