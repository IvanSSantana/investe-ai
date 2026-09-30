import logging
from pathlib import Path

from domain.ai.variation_explain_agent import VariationExplainAgent
from domain.files.csv_exporter import CSVExporter
from infrastructure.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)

class ExportPriceHistoryFiiUseCase:
    """Use Case for retrieving FII monthly financial data, analyzing variations and exporting to CSV."""

    def __init__(
        self,
        yfinance_service: YFinanceService = YFinanceService(),
        csv_exporter: CSVExporter = CSVExporter(),
        explain_agent: VariationExplainAgent = VariationExplainAgent(),
    ):
        self.yfinance_service = yfinance_service 
        self.csv_exporter = csv_exporter 
        self.explain_agent = explain_agent

    def execute(
        self, ticker: str, include_explanation: bool = True, threshold_percent: float = 2.5
    ) -> Path:
        """
        Executes the monthly price history extraction and CSV export pipeline.

        Args:
            ticker (str): Asset ticker symbol.
            include_explanation (bool): Whether AI-generated explanations should be produced or only data extraction performed.
            threshold_percent (float): Minimum absolute variation percentage to trigger AI analysis.

        Returns:
            Path: Path object pointing to the generated CSV file.
        """
        logger.info(
            f"Executing ExportPriceHistoryFiiUseCase for {ticker} (include_explanation={include_explanation})"
        )
        summaries = self.yfinance_service.get_monthly_summary(ticker)

        if not summaries:
            raise ValueError(f"No price history available for ticker '{ticker}'.")

        for month in summaries:
            price_var = month.get("price_variation_percent", 0.0)

            if include_explanation:
                if price_var >= threshold_percent:
                    explanation = self.explain_agent.explain_month(ticker, month)
                    month["explanation"] = explanation
                else:
                    month["explanation"] = "Variação dentro da normalidade"
            else:
                month["explanation"] = ""

        return self.csv_exporter.export_monthly_summary(ticker, summaries)