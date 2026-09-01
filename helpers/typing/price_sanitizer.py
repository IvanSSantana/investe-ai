import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

def price_sanitizer(price_str: str) -> Decimal | None:
    """
    Converts a price string to a float, removing currency symbols and separators.
    Example: "R$ 1.234,56" -> 1234.56
    """
    if not price_str:
        return None

    price_str = (
        price_str.replace("R$", "")
        .replace(".", "")
        .replace(",", ".")
        .replace("%", "")
        .replace(" ", "")
        .strip()
    )

    try:
        return Decimal(price_str)
    except InvalidOperation:
        logger.warning(f"An error ocurred during a price sanitizing: '{price_str}'.")
        return None