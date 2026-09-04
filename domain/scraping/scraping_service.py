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
from communication.dtos import StockResponse, RealStateFundResponse
from domain.scraping.searching import search_one_element_verifier, search_indicator_from_table
from helpers.typing.price_sanitizer import price_sanitizer

DriverFactory = Callable[[], WebDriver]
logger = logging.getLogger(__name__)

def default_driver_factory() -> WebDriver:
    """Cria um WebDriver headless do Firefox."""
    options = Options()
    options.add_argument("--headless")
    return WebDriver(service=Service(GeckoDriverManager().install()), options=options)


class ScrapingService:
    """Coleta dados do investidor10.com para um ativo: indicadores
    fundamentalistas (requests + Selenium) e links de PDFs de comunicados
    recentes (requests).
    """

    BASE_URL = "https://investidor10.com.br/{type}/{ticker}/"
    HEADERS = {"User-Agent": "Mozilla/5.0"}
    STOCK_INDICATORS_TABLE_SELECTOR = "#table-indicators article.indicator-card"
    REAL_STATE_NUMERIC_INDICATORS_TABLE_SELECTOR = "#table-indicators-history tr"
    REAL_STATE_TEXT_INDICATORS_TABLE_SELECTOR = "#table-indicators div.cell"

    STOCK_INDICATOR_FIELDS: dict[str, str] = {
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

    REAL_STATE_NUMERIC_INDICATOR_FIELDS: dict[str, str] = {
        "dividend_yield": "Dividend Yield",
        "liquidity": "Liquidez Diária",
        "vacancy_rate": "Vacância",
        "asset_value": "Valor Patrimonial",
    }

    REAL_STATE_TEXT_INDICATOR_FIELS: dict[str, str] = {
        "segment": "SEGMENTO",
        "type_fund": "TIPO DE FUNDO",
        "management_style": "TIPO DE GESTÃO"
    }

    def __init__(self, driver_factory: DriverFactory = default_driver_factory):
        self._driver_factory = driver_factory

    def search_stock_indicators(self, ticker: str) -> StockResponse:
        """Coleta preço, variações (1a/1m) e indicadores fundamentalistas."""
        url = self.BASE_URL.format(type="acoes", ticker=ticker)
        soup = self._fetch_soup(url)
        driver = self._driver_factory()

        site_ticker = search_one_element_verifier(soup, ".name-ticker h1").get_text(strip=True)
        price = price_sanitizer(
            search_one_element_verifier(soup, "div._card.cotacao div._card-body div span.value").get_text(strip=True)
        )
        segment = search_indicator_from_table("Setor", soup, "#table-indicators-company div.cell", '.title', '.value')

        # TODO: Otimizar velocidade com Selenium
        return StockResponse(
            ticker=site_ticker,
            price=price,
            value_variation_1y=self._extract_variation(url, "1y"),
            value_variation_1m=self._extract_variation(url, "1m"),
            segment=segment,
            **self._extract_stock_indicators(soup),
        )

    def search_real_state_fund_indicators(self, ticker: str) -> RealStateFundResponse:
        """Search indicators from a real state fund."""
        url = self.BASE_URL.format(type="fiis", ticker=ticker)
        soup = self._fetch_soup(url)
        
        site_ticker = search_one_element_verifier(soup, "#sub-header-logo h1").get_text(strip=True)
        price = price_sanitizer(
            search_one_element_verifier(soup, "#cards-ticker ._card-body .value").get_text(strip=True)
        )
        
        unitholders = price_sanitizer(
            search_indicator_from_table("NUMERO DE COTISTAS", soup, self.REAL_STATE_TEXT_INDICATORS_TABLE_SELECTOR, ".name", ".value")
        )

        fees = price_sanitizer(
            search_indicator_from_table("TAXA DE ADMINISTRAÇÃO", soup, self.REAL_STATE_TEXT_INDICATORS_TABLE_SELECTOR, ".name", ".value")[0:5]
        )

        return RealStateFundResponse(
            ticker=site_ticker,
            price=price,
            value_variation_1y=self._extract_variation(url, "1y"),
            value_variation_1m=self._extract_variation(url, "1m"),
            unitholders=unitholders,
            fees=fees,
            **self._extract_real_state_text_indicators(soup), # type: ignore
            **self._extract_real_state_numeric_indicators(url)
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

    def _extract_stock_indicators(self, soup: BeautifulSoup) -> dict[str, Decimal | None]:
        return {
            field: price_sanitizer(search_indicator_from_table(label, soup, self.STOCK_INDICATORS_TABLE_SELECTOR))
            for field, label in self.STOCK_INDICATOR_FIELDS.items()
        }

    def _extract_real_state_text_indicators(self, soup: BeautifulSoup) -> dict[str, str]:
        return {
            field: search_indicator_from_table(label, soup, self.REAL_STATE_TEXT_INDICATORS_TABLE_SELECTOR, ".name", ".value")
            for field, label in self.REAL_STATE_TEXT_INDICATOR_FIELS.items()
        }
    
    def _extract_real_state_numeric_indicators(self, url: str) -> dict[str, Decimal | None]:
        """Extract current real estate fund indicators from a horizontal table"""
        history_soup = self._fetch_history_table_soup(url)

        return {
            field: price_sanitizer(
                self._extract_horizontal_indicator(
                    soup=history_soup,
                    indicator=label,
                    table_selector=self.REAL_STATE_NUMERIC_INDICATORS_TABLE_SELECTOR,
                ) # type: ignore
            )
            for field, label in self.REAL_STATE_NUMERIC_INDICATOR_FIELDS.items()
        }

    def _fetch_history_table_soup(self, url: str) -> BeautifulSoup:
        """ Open the driver once per asset and wait for the indicator history table to load. """
        driver = self._driver_factory()
        try:
            driver.get(url)

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.REAL_STATE_NUMERIC_INDICATORS_TABLE_SELECTOR))
            )

            return BeautifulSoup(driver.page_source, "html.parser")

        except Exception:
            logger.warning(f"A tabela de histórico de indicadores não carregou a tempo. URL: {url}")
            return BeautifulSoup("", "html.parser")

        finally:
            driver.quit()
    
    def _extract_horizontal_indicator(self, soup: BeautifulSoup, indicator: str, table_selector: str) -> str | None:
        """Extract the current value of an indicator from a horizontal table."""
        rows = soup.select(table_selector)
        
        logger.debug(rows)
        for row in rows:
            indicator_element = row.select_one("td.indicator")
            if not indicator_element:
                continue

            logger.debug(f"Indicador elemento: {indicator_element}")
            indicator_name = indicator_element.get_text(" ", strip=True)

            if indicator_name != indicator:
                continue

            logger.debug(f"Indicador: {indicator_name}")
            values = row.select("td.value")

            if not values:
                return None

            logger.debug(f"Primeiro valor: {values[0]}")
            return values[0].get_text(" ", strip=True)

        logger.warning(f"Indicador '{indicator}' não encontrado (table_selector: {table_selector})")
        return None

    def _extract_variation(self, url: str, period: str) -> Decimal | None:
        """Extract the percentage of variation of price of an indicator.
        
        Args:
            url (str): Url from website will be scraped.
            period (str): Only accepts "1m" or "1y", corresponding a 1 month or a 1 year variation.
        """
        types = {
            "1m": 30,
            "1y": 365,
        }

        selector = (
            f'.segmented-period-bar__pills button[data-period="{types[period]}"]'
        )

        driver = self._driver_factory()

        try:
            driver.get(url)

            wait = WebDriverWait(driver, 20)

            button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))

            previous_text = driver.find_element(By.CSS_SELECTOR, "span.info-percentage").text

            button.click()
            wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, selector)))

            variation_text = driver.find_element(By.CSS_SELECTOR, "span.info-percentage").text

            return price_sanitizer(variation_text)

        except Exception:
            logger.exception(f"Erro ao extrair variação de {types[period]} dias. URL: {url}")
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
    # indicadores = service.search_stock_indicators('PETR4')
    indicators = service.search_real_state_fund_indicators('GARE11')
    print(indicators.model_dump_json(indent=4))