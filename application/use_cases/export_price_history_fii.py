from datetime import datetime
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
        cache_dir: str = "csv_cache",
    ):
        self.yfinance_service = yfinance_service  
        self.csv_exporter = csv_exporter  
        self.explain_agent = explain_agent 
        self.cache_dir = Path(cache_dir)

    def execute(
        self,
        ticker: str,
        include_explanation: bool = True,
        threshold_percent: float = 2.5,
        force_refresh: bool = False,
    ) -> Path:
        """
        Executes the monthly price history extraction and CSV export pipeline.
        """
        ticker_upper = ticker.upper()
        now_str = datetime.now().strftime("%Y_%m")
        suffix = "explained" if include_explanation else "raw"
        filename = f"{ticker_upper}_{now_str}_{suffix}.csv"

        target_file = self.cache_dir / ticker_upper / filename

        if not force_refresh and target_file.exists():
            logger.info(f"Serving CSV for {ticker_upper} from monthly cache ({filename})")
            return target_file

        logger.info(
            f"Executing ExportPriceHistoryFiiUseCase for {ticker_upper} (include_explanation={include_explanation})"
        )
        summaries = self.yfinance_service.get_monthly_summary(ticker_upper)

        if not summaries:
            raise ValueError(f"No price history available for ticker '{ticker_upper}'.")

        for month in summaries:
            price_var = month.get("price_variation_percent", 0.0)

            if include_explanation:
                if price_var >= threshold_percent:
                    explanation = self.explain_agent.explain_month(ticker_upper, month)
                    month["explanation"] = explanation
                else:
                    month["explanation"] = "Variação dentro da normalidade"
            else:
                month["explanation"] = ""

        return self.csv_exporter.export_monthly_summary(
            ticker=ticker_upper,
            summaries=summaries,
            output_dir=str(self.cache_dir),
            filename=filename,
        )