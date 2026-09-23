from communication.dtos import RealStateFundResponse
from domain.scraping.scraping_service import ScrapingService


class GetIndicatorsFiiUseCase:
    def __init__(self, scraping_service: ScrapingService = ScrapingService()):
        self._scraping_service = scraping_service

    def execute(self, ticker: str) -> RealStateFundResponse:
        return self._scraping_service.search_real_state_fund_indicators(ticker)