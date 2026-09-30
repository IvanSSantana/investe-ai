import csv
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class CSVExporter:
    def export_monthly_summary(
        self, ticker: str, summaries: list[dict[str, Any]], output_dir: str = "csv_cache"
    ) -> Path:
        """
        Exports monthly financial summaries to a CSV file including explanations.

        Args:
            ticker (str): Asset ticker symbol.
            summaries (list[dict[str, Any]]): Monthly summary records.
            output_dir (str): Cache directory for storing CSV files.

        Returns:
            Path: Path object pointing to the generated CSV file.
        """
        target_dir = Path(output_dir) / ticker.upper()
        target_dir.mkdir(parents=True, exist_ok=True)

        file_path = target_dir / "history_1y.csv"

        fieldnames = [
            "year_month",
            "initial_price",
            "final_price",
            "price_variation_percent",
            "dividends_paid",
            "dividend_yield_percent",
            "total_return_percent",
            "explanation",
        ]

        logger.info(f"Writing monthly summary CSV for {ticker} at {file_path}")

        with open(file_path, mode="w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            for row in summaries:
                if "explanation" not in row:
                    row["explanation"] = ""
                writer.writerow(row)

        return file_path