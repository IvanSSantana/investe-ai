import logging
from bs4 import Tag  
from communication.exceptions import ScrapingError

logger = logging.getLogger(__name__)

def search_one_element_verifier(soup, selector: str) -> Tag:
    """Busca um elemento usando um seletor CSS e verifica se ele existe.
    Retorna o texto do elemento se encontrado e lança um ScrapingError se não for.
    """

    element = soup.select_one(selector)
    if not element:
        raise ScrapingError(f"Element not found for selector: {selector}")
    return element


def search_indicator_from_table(indicator: str, soup, childs_selector="#table-indicators article.indicator-card", title_selector=".indicator-card-title", value_selector=".indicator-card-value") -> str:
    """Busca, por conteúdo do título (contains), um indicador dentro de um conjunto
    de cards e retorna o texto do seu valor.

    O `table_selector` ancora nos cards (ex.: `article.indicator-card`), não nos
    nós de texto — necessário porque cada card também contém números de
    comparação (Setor/Subsetor/Segmento) que não podem ser confundidos com o
    valor principal do indicador.
    """

    cards = soup.select(childs_selector)

    for card in cards:
        title = card.select_one(title_selector)
        title_text = title.get_text(strip=True) if title else ""

        if indicator.lower() in title_text.lower():
            value = card.select_one(f"{value_selector}")

            if value:
                return value.get_text(strip=True)

            logger.warning(f"O valor do indicador '{indicator}' não foi encontrado.")
            return ""

    logger.warning(f"Indicador '{indicator}' não encontrado (table_selector: {childs_selector})")
    return ""