import logging
from bs4 import Tag, BeautifulSoup
from communication.exceptions import ScrapingError

logger = logging.getLogger(__name__)

def search_one_element_verifier(soup, selector: str) -> Tag:
    """Searches for an element using a CSS selector and checks if it exists.
    Returns the element if found, and raises a ScrapingError if not.
    """

    element = soup.select_one(selector)

    if not element:
        raise ScrapingError(f"Element not found for selector: {selector}")
    
    return element

def search_indicator_from_table(
        indicator: str, 
        soup: BeautifulSoup, 
        cards_selector="#table-indicators article.indicator-card", 
        title_selector=".indicator-card-title", 
        value_selector=".indicator-card-value"
    ) -> str:
    """Searches for an indicator and returns its value from a set of cards.

    The function searches for a card whose title contains the specified
    indicator, ignoring case. Once found, it extracts and returns the text
    of the corresponding value element.

    Args:
        indicator (str): Name or partial name of the indicator to search for.
        soup (BeautifulSoup): Parsed HTML document containing the indicator cards.
        cards_selector (str): CSS selector used to locate the indicator cards.
        title_selector (str): CSS selector used to locate the title within each card.
        value_selector (str): CSS selector used to locate the value within the matching card.

    Returns:
        str: The text of the indicator's value, or an empty string if the
        indicator or its value is not found.
    """

    cards = soup.select(cards_selector)

    for card in cards:
        title = card.select_one(title_selector)
        title_text = title.get_text(strip=True) if title else ""

        if indicator.lower() in title_text.lower():
            value = card.select_one(f"{value_selector}")

            if value:
                return value.get_text(strip=True)

            logger.warning(f"The value of indicator '{indicator}' not founded.")
            return ""

    logger.warning(f"Indicator '{indicator}' not founded (table_selector: {cards_selector}).")
    return ""