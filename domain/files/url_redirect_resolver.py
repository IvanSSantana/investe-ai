import logging
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0"}

_JS_REDIRECT_PATTERN = re.compile(r'window\.location\.href\s*=\s*"([^"]+)"')

def execute(url: str) -> str | None:
    """Resolves the investidor10.com.br interstitial page's JS redirect to the real document URL."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
    except requests.exceptions.ReadTimeout:
        logger.warning(f"Fail while accessing {url}: timeout error.")
        return None
    
    # response.raise_for_status()
        # raise ScrapingError(f"Falha ao acessar a URL {url}: status code {response.status_code}")

    match = _JS_REDIRECT_PATTERN.search(response.text)
    return match.group(1) if match else None