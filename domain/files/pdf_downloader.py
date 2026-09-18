import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests

PDF_CACHE_ROOT = Path("pdf_cache")

_ILLEGAL_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')

def download_pdf(url: str, ticker: str) -> Path:
    """Downloads a communication PDF and returns its local cache path."""
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    filename = _derive_safe_filename(url, fallback=f"{ticker}.pdf")

    target = PDF_CACHE_ROOT / ticker.upper() / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(response.content)

    return target

def _derive_safe_filename(url: str, fallback: str) -> str:
    """Extracts a filesystem-safe .pdf filename from a URL's path.

    Example: "https://.../Relatorio%20Gerencial%20MXRF11.pdf?v=2"
      -> "Relatorio Gerencial MXRF11.pdf"
    """
    raw_name = Path(unquote(urlparse(url).path)).name or fallback

    safe_name = _ILLEGAL_FILENAME_CHARS.sub("_", raw_name)

    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"

    return safe_name