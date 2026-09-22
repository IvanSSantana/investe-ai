import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

from communication.exceptions import ScrapingError

PDF_CACHE_ROOT = Path("pdf_cache")
HEADERS = {"User-Agent": "Mozilla/5.0"}

_ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')
_PDF_MAGIC_BYTES = b"%PDF"
_JS_REDIRECT_PATTERN = re.compile(r'window\.location\.href\s*=\s*"([^"]+)"')

def download_pdf(url: str, ticker: str) -> Path:
    """Downloads a communication PDF and returns its local cache path."""
    filename = _derive_safe_filename(url, fallback=f"{ticker}.pdf")

    final_url = _resolve_redirect_url(url)

    response = requests.get(final_url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    if not response.content.startswith(_PDF_MAGIC_BYTES):
        preview = response.content[:30]
        raise ScrapingError(f"URL não retornou um PDF válido (conteúdo começa com {preview!r}): {final_url}")

    target = PDF_CACHE_ROOT / ticker.upper() / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)

    return target

def _resolve_redirect_url(url: str) -> str:
    """Resolves the investidor10.com.br interstitial page's JS redirect to the real document URL."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()

    match = _JS_REDIRECT_PATTERN.search(response.text)
    return match.group(1) if match else url

def _derive_safe_filename(url: str, fallback: str) -> str:
    """Extracts a filesystem-safe .pdf filename from a URL's path.

    Ex.: "https://investidor10.com.br/fiis/link_comunicado/MXRF11/26451/"
      -> "26451.pdf"
    """
    raw_name = Path(unquote(urlparse(url).path)).name or fallback

    safe_name = _ILLEGAL_FILENAME_CHARS.sub("_", raw_name)

    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"

    return safe_name
