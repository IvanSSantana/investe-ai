from decimal import Decimal

from communication.dtos import RealStateFundResponse
from helpers.typing.number_formatter import number_formatter

VACANCY_HIGH = Decimal("10")          
LIQUIDITY_LOW = Decimal("750000")    
ADMIN_FEE_HIGH = Decimal("1")         
DIVIDEND_YIELD_MEANINGFUL_DIFF = Decimal("2")  
ASSET_VALUE_LOW = Decimal("1000000000")

def interpret_indicators(fund: RealStateFundResponse) -> dict[str, str]:
    """Generates a brief textual interpretation for indicators."""
    return {
        "DIVIDEND_YIELD_INTERPRETACAO": _interpret_dividend_yield(
            fund.dividend_yield, fund.dividend_yield_segment_average
        ),
        "VACANCIA_INTERPRETACAO": _interpret_vacancy(fund.vacancy_rate),
        "LIQUIDEZ_INTERPRETACAO": _interpret_liquidity(fund.liquidity),
        "TAXA_INTERPRETACAO": _interpret_admin_fee(fund.fees),
        "VALOR_PATRIMONIAL_INTERPRETACAO": _interpret_asset_value(fund.asset_value),
    }

def _interpret_dividend_yield(value: Decimal | None, segment_average: Decimal | None) -> str:
    if value is None:
        return "Dado não disponível."

    if segment_average is None:
        return f"{value}% ao ano — não foi possível comparar com a média do segmento (dado indisponível)."

    diff = value - segment_average

    if diff >= DIVIDEND_YIELD_MEANINGFUL_DIFF:
        return (
            f"{value}% ao ano, acima da média do tipo/segmento ({segment_average}%) — "
            f"yield elevado frente aos pares; vale checar se a distribuição é sustentável ou pontual."
        )
    if diff <= -DIVIDEND_YIELD_MEANINGFUL_DIFF:
        return f"{value}% ao ano, abaixo da média do tipo/segmento ({segment_average}%) — yield baixo frente aos pares."

    return f"{value}% ao ano, próximo da média do tipo/segmento ({segment_average}%)."

def _interpret_vacancy(value: Decimal | None) -> str:
    if value is None:
        return "Dado não disponível."
    if value >= VACANCY_HIGH:
        return f"Acima de {VACANCY_HIGH}% — vacância considerada alta; pode pressionar a receita futura do fundo."
    return f"Abaixo de {VACANCY_HIGH}% — vacância considerada controlada."

def _interpret_liquidity(value: Decimal | None) -> str:
    if value is None:
        return "Dado não disponível."
    if value < LIQUIDITY_LOW:
        return "Abaixo de R$ 750 mil/dia — liquidez baixa; comprar ou vender posições maiores pode mover o preço."
    return "Acima de R$ 750 mil/dia — liquidez considerada razoável para negociação no dia a dia."

def _interpret_admin_fee(value: Decimal | None) -> str:
    if value is None:
        return "Dado não disponível."
    if value > ADMIN_FEE_HIGH:
        return f"Acima de {ADMIN_FEE_HIGH}% ao ano — taxa de administração relativamente alta frente à média do setor."
    return f"Até {ADMIN_FEE_HIGH}% ao ano — taxa de administração dentro da faixa considerada baixa para o setor."

def _interpret_asset_value(value: Decimal | None) -> str:
    if value is None:
        return "Dado não disponível."
    if value < ASSET_VALUE_LOW:
        return f"Abaixo de R$ {number_formatter(ASSET_VALUE_LOW)} — valor patrimonial baixo; pode indicar risco ou oportunidade de investimento."
    return f"Acima de R$ {number_formatter(ASSET_VALUE_LOW)} — valor patrimonial considerado razoável para o setor."