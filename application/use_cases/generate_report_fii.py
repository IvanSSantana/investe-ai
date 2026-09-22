import logging
from pathlib import Path

from domain.ai.ai_service import AiService
from domain.ai.vectorstore import VectorstoreService
from domain.files import pdf_downloader, report_builder
from domain.scraping.scraping_service import ScrapingService
from repository.report_registry import ReportRegistry

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

    def execute(self, ticker: str) -> Path | None:
        # For debugging while filter by 'Relatório Gerencial' has not yet been implemented
        pdf_urls = [self._scraping_service.search_pdfs(ticker, asset_type="fiis")[1]]

        if not pdf_urls:
            logger.warning(f"No recent announcements found for {ticker} — no report will be generated.")
            return None

        cached_report = self._get_cached_report_if_unchanged(ticker, pdf_urls)
        if cached_report is not None:
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
            file_path = pdf_downloader.download_pdf(url, ticker)
            self._vectorstore_service.insert_to_db(knowledge, str(file_path))

        events = self._ai_service.extract_events_from_fund(knowledge)
        conclusion = self._ai_service.generate_conclusion(events)
        markdown = report_builder.generate_markdown_report(fund, events, conclusion)
        report_path = report_builder.save_markdown_report(markdown, ticker)

        self._report_registry.record_generation(ticker, report_path, pdf_urls)

        return report_path

if __name__ == "__main__":
    usecase = GenerateReportFiiUseCase()
    usecase.execute("MXRF11")
