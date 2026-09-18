from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from communication.dtos import RealStateFundResponse
from domain.files.indicator_interpreter import interpret_indicators

DEFAULT_TEMPLATE_PATH = Path(__file__).parent / "templates" / "report_fii.md"
REPORTS_ROOT = Path("reports_db")

def generate_markdown_report(
    fund: RealStateFundResponse,
    events: list[dict[str, Any]],
    conclusion: str | None,
    template_path: str | Path = DEFAULT_TEMPLATE_PATH,
) -> str:
    template = Path(template_path).read_text(encoding="utf-8")

    placeholders = _build_placeholders(fund, events, conclusion)

    for key, value in placeholders.items():
        template = template.replace(f"{{{{{key}}}}}", value)

    return template

def save_markdown_report(markdown: str, ticker: str) -> Path:
    """Saves a Markdown report and returns its generated path."""
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_ROOT / f"{ticker.upper()}_{timestamp}.md"

    path.write_text(markdown, encoding="utf-8")

    return path

def _build_placeholders(
    fund: RealStateFundResponse,
    events: list[dict[str, Any]],
    conclusion: str | None,
) -> dict[str, str]:
    return {
        "TICKER": fund.ticker, # type: ignore
        "PRECO": _format_currency(fund.price),
        "VARIACAO_1M": _stringify(fund.value_variation_1m),
        "VARIACAO_1Y": _stringify(fund.value_variation_1y),
        "DIVIDEND_YIELD": _stringify(fund.dividend_yield),
        "LIQUIDEZ": _format_currency(fund.liquidity),
        "VACANCIA": _stringify(fund.vacancy_rate),
        "VALOR_PATRIMONIAL": _format_currency(fund.asset_value),
        "SEGMENTO": _stringify(fund.segment),
        "TIPO_FUNDO": _stringify(fund.type_fund),
        "TIPO_GESTAO": _stringify(fund.management_style),
        "COTISTAS": _stringify(fund.unitholders),
        "TAXA": _stringify(fund.fees),
        **interpret_indicators(fund),
        "EVENTOS": _format_events_to_markdown(events),
        "CONCLUSAO": conclusion or "Nenhuma conclusão gerada.",
        "DATA": datetime.now().strftime("%d/%m/%Y"),
    }

def _format_events_to_markdown(events: list[dict[str, Any]]) -> str:
    """Formats extracted events as Markdown sections."""
    if not events:
        return "Nenhum evento relevante encontrado no período."

    return "\n\n".join(
        f"### {event.get('titulo', '')}\n"
        f"{event.get('descricao', '')}\n\n"
        f"**Impacto no preço:** {event.get('impacto', '')}\n"
        f"**Importância:** {event.get('importancia', '')}"
        for event in events
    )

def _format_currency(value: Decimal | None) -> str:
    if value is None:
        return "Dado não disponível"

    return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")

def _stringify(value: Any) -> str:
    """Converts a value to string, returning an empty string for None."""
    return "" if value is None else str(value)