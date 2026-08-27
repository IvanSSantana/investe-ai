from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Callable
import logging

import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

from communication.exceptions import ScrapingError
from communication.dtos import StockResponse
from domain.scraping.searching import search_one_element_verifier, search_indicator
from helpers.typing.price_sanitizer import price_sanitizer

DriverFactory = Callable[[], WebDriver]
logger = logging.getLogger(__name__)

def default_driver_factory() -> WebDriver:
    """Cria um WebDriver headless do Firefox.

    Isolado numa função própria (e não direto no __init__) para que o
    ScrapingService possa receber outra factory em testes -- ex.: uma que
    devolve um driver mockado, sem precisar subir um navegador de verdade.
    """
    options = Options()
    options.add_argument("--headless")
    return WebDriver(service=Service(GeckoDriverManager().install()), options=options)


class ScrapingService:
    """Coleta dados do investidor10.com para um ativo: indicadores
    fundamentalistas (requests + Selenium) e links de PDFs de comunicados
    recentes (requests).
    """

    BASE_URL = "https://investidor10.com.br/acoes/{ticker}/"
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    INDICATORS_TABLE_SELECTOR = "#table-indicators article.indicator-card"

    INDICATOR_FIELDS: dict[str, str] = {
        "pl": "P/L",
        "pvp": "P/VP",
        "dividend_yield": "Dividend Yield",
        "roe": "ROE",
        "roic": "ROIC",
        "net_debt_to_EBITDA": "Divida Liquida/EBITDA",
        "ev_to_EBITDA": "EV/EBITDA",
        "profit_cagr": "CAGR Lucros ",
        "payout": "Payout",
        "net_margin": "Margem Líquida",
        "ebit_margin": "Margem Ebit",
    }

    def __init__(self, driver_factory: DriverFactory = default_driver_factory):
        self._driver_factory = driver_factory

    def search_indicators(self, ticker: str) -> StockResponse:
        """Coleta preço, variações (1a/1m) e indicadores fundamentalistas."""
        url = self.BASE_URL.format(ticker=ticker)
        soup = self._fetch_soup(url)

        site_ticker = search_one_element_verifier(soup, ".name-ticker h1").get_text(strip=True)
        price = price_sanitizer(
            search_one_element_verifier(soup, "div._card.cotacao div._card-body div span.value").get_text(strip=True)
        )
        segment = search_indicator("Setor", soup, "#table-indicators-company div.cell", '.title', '.value')

        # TODO: Otimizar velocidade com Selenium
        return StockResponse(
            ticker=site_ticker,
            price=price,
            value_variation_1y=self._extract_1y_variation(soup),
            value_variation_1m=self._extract_1m_variation(url),
            segment=segment,
            **self._extract_indicators(soup),
        )

    def search_pdfs(self, ticker: str) -> list[str]:
        """Retorna os links de PDFs de comunicados publicados no último mês."""
        url = self.BASE_URL.format(ticker=ticker)
        soup = self._fetch_soup(url)

        pdfs_area = search_one_element_verifier(soup, "section#communications-section div.content div.row")
        cards = pdfs_area.select("div.col-12 div.communication-card")

        return [
            link for card in cards
            if (link := self._extract_recent_pdf_link(card)) is not None
        ]

    def _fetch_soup(self, url: str) -> BeautifulSoup:
        response = requests.get(url, headers=self.HEADERS)
        response.encoding = "utf-8"

        if response.status_code != 200:
            raise ScrapingError(f"Error while accessing the website: {url}")

        return BeautifulSoup(response.text, "html.parser")

    def _extract_indicators(self, soup: BeautifulSoup) -> dict[str, Decimal | None]:
        return {
            field: price_sanitizer(search_indicator(label, soup, self.INDICATORS_TABLE_SELECTOR))
            for field, label in self.INDICATOR_FIELDS.items()
        }

    def _extract_1y_variation(self, soup: BeautifulSoup) -> Decimal | None:
        variation = price_sanitizer(
            search_one_element_verifier(soup, "div._card.pl div._card-body div span").get_text(strip=True)
        )
        if variation is None: return

        img_variation = soup.select_one("div._card.pl div._card-body div img")
        if img_variation and "seta-down" in (img_variation.get("src") or ""):
            variation = -variation if variation else variation

        return variation

    def _extract_1m_variation(self, url: str) -> Decimal | None:
        """A variação de 1 mês só carrega após um clique, por isso exige Selenium."""
        selector = (
            '.segmented-period-bar__pills > button[data-period="30"]'
        )

        driver = self._driver_factory()
        try:
            driver.get(url)

            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
            driver.find_element(By.CSS_SELECTOR, selector).click()

            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".info-percentage")))
            variation_text = driver.find_element(By.CSS_SELECTOR, "span.info-percentage").text

            return price_sanitizer(variation_text)
        except Exception as error:
            logger.warning(f"O botão para definir o período de variação para 30 dias não foi encontrado. Seletor: {selector}")
            return None
        finally:
            driver.quit()

    def _extract_recent_pdf_link(self, card) -> str | None:
        """Retorna o link do PDF do card, ou None se tiver mais de 30 dias."""
        date_element = card.select_one("div.card-date span.card-date--content")
        if date_element:
            report_date = datetime.strptime(date_element.get_text(strip=True), "%d/%m/%Y")
            if report_date < datetime.now() - timedelta(days=30):
                return None

        download_button = card.select_one("a.btn-download-communication")
        return download_button.get("href") if download_button else None

if __name__ == "__main__":
    service = ScrapingService()
    indicadores = service.search_indicators('PETR4')
    print(indicadores.model_dump_json(indent=4))