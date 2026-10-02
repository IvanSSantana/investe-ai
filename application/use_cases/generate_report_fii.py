from datetime import datetime
import logging
from pathlib import Path

from domain.ai.ai_service import AiService
from domain.ai.vectorstore import VectorstoreService
from domain.files import report_builder, url_redirect_resolver
from domain.scraping.scraping_service import ScrapingService
from repository.report_registry import ReportRegistry

from communication.exceptions import NoDataForExportError, PDFDownloadFailedException

logger = logging.getLogger(__name__)

class GenerateReportFiiUseCase:
    def __init__(
        self,
        ai_service: AiService | None = None,
        scraping_service: ScrapingService = ScrapingService(),
        vectorstore_service: VectorstoreService = VectorstoreService(),
        report_registry: ReportRegistry = ReportRegistry(),
    ):
        self._scraping_service = scraping_service
        self._vectorstore_service = vectorstore_service
        self._ai_service = ai_service if ai_service else AiService(self._vectorstore_service)
        self._report_registry = report_registry

    def execute(self, ticker: str, force_refresh: bool = False) -> Path:
        """
        Executes report generation or fetches from cache if valid.
        """
        ticker_upper = ticker.upper()
        now_str = datetime.now().strftime("%Y_%m")
        cached_report = Path("pdf_cache") / ticker_upper / f"{ticker_upper}_{now_str}.pdf"

        if not force_refresh and cached_report.exists():
            logger.info(f"Serving cached report for {ticker_upper}: {cached_report.name}")
            return cached_report

        logger.info(f"Generating new report for {ticker_upper}")
        pdf_urls = self._scraping_service.search_pdfs(ticker, asset_type="fiis")

        if not pdf_urls:
            raise NoDataForExportError(f"No recent announcements found for {ticker} — no report will be generated.")

        cached_report = self._get_cached_report_if_unchanged(ticker, pdf_urls)
        if cached_report is not None:
            logger.warning(f"Report for {ticker} is up-to-date. Returning cached report at {cached_report}.")
            return cached_report

        return self._generate_new_report(ticker, pdf_urls)

    def _get_cached_report_if_unchanged(self, ticker: str, pdf_urls: list[str]) -> Path | None:
        last_generation = self._report_registry.get_last_generation(ticker)

        if last_generation is None:
            return None

        if set(last_generation.source_pdfs) != set(pdf_urls):
            return None  

        return last_generation.report_path

    def _generate_new_report(self, ticker: str, pdf_urls: list[str]) -> Path:
        fund = self._scraping_service.search_real_state_fund_indicators(ticker)

        vector_db = self._vectorstore_service.build_vectorstore(ticker)
        knowledge = self._vectorstore_service.get_or_create_knowledge(vector_db, ticker)

        for url in pdf_urls:
            url = url_redirect_resolver.execute(url)
            if url:
                self._vectorstore_service.insert_to_db(knowledge, url, ticker)

        if not self._has_valid_cached_files(ticker):
            logger.error(f"Failed to locate valid downloaded PDFs for {ticker}.")
            raise PDFDownloadFailedException(ticker)

        events = self._ai_service.extract_events_from_fund(knowledge)
        conclusion = self._ai_service.generate_conclusion(events, ticker)
        markdown = report_builder.generate_markdown_report(fund, events, conclusion)
        report_path = report_builder.save_markdown_report(markdown, ticker)

        self._report_registry.record_generation(ticker, report_path, pdf_urls)

        return report_path

    def _has_valid_cached_files(self, ticker: str) -> bool:
        """Checks if there is at least one valid, non-empty markdown cached in disk."""
        cache_dir = Path("md_cache") / ticker.upper()
        if not cache_dir.exists():
            return False
        
        return any(file.stat().st_size > 0 for file in cache_dir.glob("*.md"))

if __name__ == "__main__":
    usecase = GenerateReportFiiUseCase()
    usecase.execute("MXRF11")
