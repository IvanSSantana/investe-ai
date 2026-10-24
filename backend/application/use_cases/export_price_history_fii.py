from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any, Literal

from domain.ai.variation_explain_agent import VariationExplainAgent
from domain.files.csv_exporter import CSVExporter
from infrastructure.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)

class ExportPriceHistoryFiiUseCase:
    """Use Case for retrieving FII monthly financial data, analyzing variations and exporting."""

    _PERIOD_BY_OUTPUT_TYPE: dict[str, str] = {
        "csv": "1y",
        "json": "5y",
    }

    def __init__(
        self,
        yfinance_service: YFinanceService = YFinanceService(),
        csv_exporter: CSVExporter = CSVExporter(),
        explain_agent: VariationExplainAgent = VariationExplainAgent(),
        cache_dir: str = "price_history_cache",
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
        output_type: Literal["csv", "json"] = "csv",
    ) -> Path | list[dict[str, Any]]:
        """
        Executes the monthly price history extraction pipeline.

        Args:
            ticker: FII ticker symbol.
            include_explanation: If True, invokes the LLM for months where
                ``price_variation_percent >= threshold_percent``.
            threshold_percent: Minimum absolute variation to trigger an explanation.
            force_refresh: If True, bypasses the monthly cache.
            output_type: "csv" writes a CSV file and returns its Path (period="1y").
                         "json" returns the raw list of monthly summaries (period="5y").

        Raises:
            ValueError: If no data is available or ``output_type`` is invalid.
        """
        if output_type not in self._PERIOD_BY_OUTPUT_TYPE:
            raise ValueError(
                f"Invalid output_type: {output_type!r}. Expected 'csv' or 'json'."
            )

        ticker_upper = ticker.upper()
        now_str = datetime.now().strftime("%Y_%m")
        suffix = "explained" if include_explanation else "raw"
        period = self._PERIOD_BY_OUTPUT_TYPE[output_type]

        cache_dir = self.cache_dir / ticker_upper
        cache_file = cache_dir / f"{ticker_upper}_{now_str}_{suffix}.{output_type}"

        if not force_refresh and cache_file.exists():
            if output_type == "csv":
                logger.info(f"Serving CSV for {ticker_upper} from cache ({cache_file.name})")
                return cache_file

            try:
                logger.info(f"Serving JSON for {ticker_upper} from cache ({cache_file.name})")
                return json.loads(cache_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(
                    f"Corrupted JSON cache for {ticker_upper} ({exc}); rebuilding."
                )

        logger.info(
            f"Executing ExportPriceHistoryFiiUseCase for {ticker_upper} "
            f"(output_type={output_type}, period={period}, "
            f"include_explanation={include_explanation})"
        )
        summaries = self.yfinance_service.get_monthly_summary(ticker_upper, period=period)

        if not summaries:
            raise ValueError(f"No price history available for ticker '{ticker_upper}'.")

        for month in summaries:
            price_var = month.get("price_variation_percent", 0.0)

            if include_explanation:
                if abs(price_var) >= threshold_percent:
                    month["explanation"] = self.explain_agent.explain_month(
                        ticker_upper, month
                    )
                else:
                    month["explanation"] = "Variação dentro da normalidade"
            else:
                month["explanation"] = ""

        if output_type == "json":
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(
                json.dumps(summaries, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return summaries

        return self.csv_exporter.export_monthly_summary(
            ticker=ticker_upper,
            summaries=summaries,
            output_dir=str(self.cache_dir),
            filename=cache_file.name,
        )