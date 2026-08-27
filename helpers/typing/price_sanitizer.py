import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

def price_sanitizer(price_str: str) -> Decimal | None:
    """
    Converte uma string de preço para um float, removendo símbolos de moeda e separadores.
    Exemplo: "R$ 1.234,56" -> 1234.56
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
        logger.warning(f"Houve um erro durante a sanitização de um número: '{price_str}'.")
        return None