from datetime import datetime
import json
import logging
from pathlib import Path
from typing import Any

from domain.scraping.scraping_service import ScrapingService
from communication.dtos import RealStateFundResponse

logger = logging.getLogger(__name__)

class GetIndicatorsFiiUseCase:
    """Use case for retrieving FII indicators with daily file-based caching."""

    def __init__(
        self,
        scraping_service: ScrapingService = ScrapingService(),
        cache_dir: str = "indicators_cache",
    ):
        self.scraping_service = scraping_service 
        self.cache_dir = Path(cache_dir)

    def execute(self, ticker: str, force_refresh: bool = False) -> RealStateFundResponse:
        """
        Retrieves indicators for a given FII ticker. Uses daily cache unless force_refresh is True.
        """
        ticker_upper = ticker.upper()
        today_str = datetime.now().strftime("%Y_%m_%d")
        target_dir = self.cache_dir / ticker_upper
        target_dir.mkdir(parents=True, exist_ok=True)

        cache_file = target_dir / f"{ticker_upper}_{today_str}.json"

        if not force_refresh and cache_file.exists():
            logger.info(f"Serving indicators for {ticker_upper} from daily cache ({cache_file.name})")
            with open(cache_file, "r", encoding="utf-8") as file:
                return json.load(file)

        logger.info(f"Fetching fresh indicators for {ticker_upper} via scraping")
        data = self.scraping_service.search_real_state_fund_indicators(ticker_upper)

        if data:
            self._purge_old_caches(target_dir, today_str)
            with open(cache_file, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=2)

        return data

    def _purge_old_caches(self, target_dir: Path, today_str: str) -> None:
        """Deletes older indicator JSON files for this ticker."""
        for file in target_dir.glob("*.json"):
            if today_str not in file.name:
                try:
                    file.unlink()
                    logger.info(f"Purged old indicators cache file: {file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete old cache file {file.name}: {e}")