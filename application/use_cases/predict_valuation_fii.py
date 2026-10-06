import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from application.use_cases.generate_report_fii import GenerateReportFiiUseCase
from application.use_cases.get_indicators_fii import GetIndicatorsFiiUseCase
from communication.dtos import RealStateFundResponse, ValuationPredictionResponse
from domain.ai.ai_service import AiService
from domain.ai.vectorstore import VectorstoreService
from domain.files import url_redirect_resolver
from domain.scraping.scraping_service import ScrapingService
from infrastructure.market_data_service import MarketDataService
from infrastructure.yfinance_service import YFinanceService

logger = logging.getLogger(__name__)

class PredictValuationFiiUseCase:
    """Use case for predicting FII short-term and medium-term valuation integrated with real indicators."""

    def __init__(
        self,
        ai_service: AiService = AiService(),
        get_indicators_use_case: GetIndicatorsFiiUseCase = GetIndicatorsFiiUseCase(),
        generate_report_use_case: GenerateReportFiiUseCase = GenerateReportFiiUseCase(),
        yfinance_service: YFinanceService = YFinanceService(),
        market_data_service: MarketDataService = MarketDataService(),
        scraping_service: ScrapingService = ScrapingService(),
        vectorstore_service: VectorstoreService = VectorstoreService(),
        cache_dir: str = "prediction_cache",
    ):
        self._ai_service = ai_service
        self._get_indicators_use_case = get_indicators_use_case
        self._generate_report_use_case = generate_report_use_case
        self._yfinance_service = yfinance_service
        self._market_data_service = market_data_service
        self._scraping_service = scraping_service
        self._vectorstore_service = vectorstore_service
        self._cache_dir = Path(cache_dir)

    def execute(self, ticker: str, force_refresh: bool = False) -> ValuationPredictionResponse:
        """Fetches dynamic indicators, historical series, risk-free rate, and executes valuation pipeline.
        Uses monthly file-based cache unless force_refresh is True; on cache hits, only the
        current price and its derived numeric fields are refreshed."""
        ticker_upper = ticker.upper()
        logger.info(f"Executing Integrated Valuation Prediction Use Case for {ticker_upper}")

        today_str = datetime.now().strftime("%Y_%m")
        target_dir = self._cache_dir / ticker_upper
        target_dir.mkdir(parents=True, exist_ok=True)
        cache_file = target_dir / f"{ticker_upper}_{today_str}.json"

        if not force_refresh and cache_file.exists():
            logger.info(f"Serving prediction for {ticker_upper} from monthly cache ({cache_file.name})")
            return self._serve_cached_prediction(cache_file, ticker_upper)

        raw_indicators = self._get_indicators_use_case.execute(ticker_upper)

        if isinstance(raw_indicators, dict):
            indicators = RealStateFundResponse(**raw_indicators)
        else:
            indicators = raw_indicators

        current_price = Decimal(str(indicators.price))  
        vp_per_share = Decimal(str(indicators.vp_per_share))

        pvp = Decimal(str(indicators.pvp))  

        history = self._yfinance_service.get_price_history(f"{ticker_upper}.SA")

        recent_dpus: list[Decimal] = []
        if not history.empty and "Dividends" in history.columns:
            dividends = history["Dividends"][history["Dividends"] > 0]
            if not dividends.empty:
                recent_dpus = [Decimal(str(value)) for value in dividends.tail(3).tolist()]

        if not recent_dpus:
            logger.warning(
                f"No dividend history found for {ticker_upper}. Estimating DPU from current price and dividend yield."
            )
            annual_dy_percent = Decimal(str(indicators.dividend_yield))  

            estimated_monthly_dpu = (current_price * (annual_dy_percent / Decimal("100"))) / Decimal("12")
            recent_dpus = [estimated_monthly_dpu]

        risk_free_rate = Decimal(str(self._market_data_service.get_current_risk_free_rate()))

        historical_mean_pvp = Decimal(str(self._scraping_service.extract_historical_mean_pvp(ticker_upper)))

        self._generate_report_use_case.execute(ticker_upper)

        prediction = self._ai_service.predict_valuation(
            ticker=ticker_upper,
            current_price=current_price,
            vp_per_share=vp_per_share,
            pvp=pvp,
            recent_dpus=recent_dpus,
            risk_free_rate=risk_free_rate,
            historical_mean_pvp=historical_mean_pvp
        )

        self._purge_old_caches(target_dir, today_str)
        self._save_to_cache(cache_file, prediction)

        return prediction

    def _serve_cached_prediction(self, cache_file: Path, ticker_upper: str) -> ValuationPredictionResponse:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        prediction = ValuationPredictionResponse(**payload["prediction"])

        return self._refresh_current_price(prediction, ticker_upper)

    def _refresh_current_price(
        self,
        prediction: ValuationPredictionResponse,
        ticker_upper: str,
    ) -> ValuationPredictionResponse:
        """Updates only the price-derived numeric fields; LLM-generated texts stay frozen
        as of the generation date."""
        raw_indicators = self._get_indicators_use_case.execute(ticker_upper, force_refresh=True)

        if isinstance(raw_indicators, dict):
            indicators = RealStateFundResponse(**raw_indicators)
        else:
            indicators = raw_indicators

        if indicators.price is None:
            logger.warning(f"No current price available for {ticker_upper}. Serving cached prediction as-is.")
            return prediction

        current_price = indicators.price
        prediction.preco_atual = round(current_price, 2)

        prediction.pvp_atual = Decimal(str(indicators.pvp))  

        fair_mid_price = (
            prediction.medio_prazo.preco_justo_min + prediction.medio_prazo.preco_justo_max
        ) / 2

        if current_price > 0:
            prediction.medio_prazo.upside_downside_percent = round(
                ((fair_mid_price - current_price) / current_price) * 100, 2
            )

        logger.info(
            f"Cached prediction for {ticker_upper} refreshed with current price: R$ {current_price}"
        )
        return prediction

    def _save_to_cache(
        self,
        cache_file: Path,
        prediction: ValuationPredictionResponse,
    ) -> None:
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "prediction": prediction.model_dump(mode="json")
        }
        cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Prediction cached at: {cache_file}")

    def _purge_old_caches(self, target_dir: Path, now_str: str) -> None:
        """Deletes prediction JSON files from previous months for this ticker."""
        for file in target_dir.glob("*.json"):
            if now_str not in file.name:
                try:
                    file.unlink()
                    logger.info(f"Purged old prediction cache file: {file.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete old cache file {file.name}: {e}")