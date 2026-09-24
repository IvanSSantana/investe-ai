import logging
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)

SCALE_THRESHOLDS = (
    (Decimal("1_000_000_000"), "B"),
    (Decimal("1_000_000"), "M"),
    (Decimal("1_000"), "mil"),
)

def number_formatter(
    value: Decimal | None,
    decimals: int = 2,
    compact: bool = True,
) -> str:
    """
    Formats a numeric value into a Brazilian Portuguese formatted string.
    Optionally compacts large numbers using 'mil', 'M', and 'B' scale suffixes.

    Examples:
        Decimal("1234567.89") -> "1,23 M"
        Decimal("750000") -> "750,00 mil"
        Decimal("1234.56"), compact=False -> "1.234,56"
        None -> "Dado não disponível"
    """
    if value is None:
        return "Dado não disponível"

    try:
        num = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        logger.warning(f"An error occurred during number formatting: '{value}'.")
        return "Dado não disponível"

    if num == Decimal(0):
        return "0,00" if decimals > 0 else "0"

    is_negative = num < Decimal(0)

    if compact:
        for threshold, suffix in SCALE_THRESHOLDS:
            if num >= threshold:
                scaled_value = num / threshold
                formatted_scaled = f"{scaled_value:.{decimals}f}".replace(".", ",")
                prefix = "-" if is_negative else ""
                return f"{prefix}{formatted_scaled} {suffix}"

    formatted_str = f"{num:.{decimals}f}"
    integer_part, decimal_part = formatted_str.split(".")

    integer_formatted = f"{int(integer_part):,}".replace(",", ".")

    prefix = "-" if is_negative else ""
    return f"{prefix}{integer_formatted},{decimal_part}"