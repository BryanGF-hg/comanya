import requests
import time
import random
from tenacity import retry, stop_after_attempt, wait_exponential

_session = requests.Session()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(1, 2, 6))
def get(url: str, timeout: int = 10) -> str:
    time.sleep(random.uniform(0.4, 1.2))
    r = _session.get(
        url,
        timeout=timeout,
        headers={
            "User-Agent": random.choice([
                "Mozilla/5.0 Chrome/124",
                "Mozilla/5.0 Firefox/125",
                "Mozilla/5.0 Safari/17"
            ])
        }
    )
    r.raise_for_status()
    return r.text
