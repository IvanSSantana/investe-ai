import logging
import re

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
    
    match = _JS_REDIRECT_PATTERN.search(response.text)
    return match.group(1) if match else None