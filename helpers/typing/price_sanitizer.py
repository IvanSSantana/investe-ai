import logging
import re
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

def price_sanitizer(price_str: str) -> Decimal | None:
    """
    Converts a price string to a float, removing currency symbols and separators.
    Example: "R$ 1.234,56" -> 1234.56
    """
    if not price_str:
        return None
    
    _SCALE_SUFFIXES = {
        "K": Decimal("1_000"),
        "M": Decimal("1_000_000"),
        "B": Decimal("1_000_000_000"),
    }

    price_str = (
        price_str.replace("R$", "")
        .replace(".", "")
        .replace(",", ".")
        .replace("%", "")
        .replace(" ", "")
        .strip()
    )

    scale = Decimal(1)
    if price_str and price_str[-1].upper() in _SCALE_SUFFIXES:
        scale = _SCALE_SUFFIXES[price_str[-1].upper()]
        price_str = price_str[:-1].strip()

    price_sanitized = Decimal(price_str) * scale
    
    try:
        return price_sanitized
    except InvalidOperation:
        logger.warning(f"An error ocurred during a price sanitizing: '{price_str}'.")
        return None