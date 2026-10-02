import json
import logging
from datetime import datetime
from decimal import Decimal
from pathlib import Path

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
        yfinance_service: YFinanceService = YFinanceService(),
        market_data_service: MarketDataService = MarketDataService(),
        scraping_service: ScrapingService = ScrapingService(),
        vectorstore_service: VectorstoreService = VectorstoreService(),
        cache_dir: str = "prediction_cache",
    ):
        self._ai_service = ai_service
        self._get_indicators_use_case = get_indicators_use_case
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

        current_price = float(indicators.price)  # type: ignore
        vp_per_share = float(indicators.asset_value) # type: ignore

        pvp = round(current_price / vp_per_share, 2)

        history = self._yfinance_service.get_price_history(f"{ticker_upper}.SA")

        recent_dpus: list[float] = []
        if not history.empty and "Dividends" in history.columns:
            dividends = history["Dividends"][history["Dividends"] > 0]
            if not dividends.empty:
                recent_dpus = [float(value) for value in dividends.tail(3).tolist()]

        if not recent_dpus:
            logger.warning(
                f"No dividend history found for {ticker_upper}. Estimating DPU from current price and dividend yield."
            )
            annual_dy_percent = float(indicators.dividend_yield) # type: ignore

            estimated_monthly_dpu = (current_price * (annual_dy_percent / 100.0)) / 12.0
            recent_dpus = [estimated_monthly_dpu]

        risk_free_rate = self._market_data_service.get_current_risk_free_rate()

        historical_mean_pvp = self._scraping_service.extract_historical_mean_pvp(ticker_upper)

        self._get_management_reports(ticker_upper)

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
        self._save_to_cache(cache_file, prediction, vp_per_share)

        return prediction

    def _get_management_reports(self, ticker_upper: str) -> None:
        """Searches recent management reports and indexes them into the RAG knowledge base."""
        pdf_urls = self._scraping_service.search_pdfs(ticker_upper, asset_type="fiis")

        if not pdf_urls:
            logger.warning(
                f"No recent management reports found for {ticker_upper}. "
                "Valuation will run over whatever is already indexed in the RAG."
            )
            return

        vector_db = self._vectorstore_service.build_vectorstore(ticker_upper)
        knowledge = self._vectorstore_service.get_or_create_knowledge(vector_db, ticker_upper)

        for url in pdf_urls:
            resolved_url = url_redirect_resolver.execute(url)
            if resolved_url:
                self._vectorstore_service.insert_to_db(knowledge, resolved_url, ticker_upper)

    def _serve_cached_prediction(self, cache_file: Path, ticker_upper: str) -> ValuationPredictionResponse:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        prediction = ValuationPredictionResponse(**payload["prediction"])
        vp_per_share = float(payload.get("vp_per_share") or 0.0)

        return self._refresh_current_price(prediction, ticker_upper, vp_per_share)

    def _refresh_current_price(
        self,
        prediction: ValuationPredictionResponse,
        ticker_upper: str,
        vp_per_share: float,
    ) -> ValuationPredictionResponse:
        """Updates only the price-derived numeric fields; LLM-generated texts stay frozen
        as of the generation date."""
        raw_indicators = self._get_indicators_use_case.execute(ticker_upper)

        if isinstance(raw_indicators, dict):
            indicators = RealStateFundResponse(**raw_indicators)
        else:
            indicators = raw_indicators

        if indicators.price is None:
            logger.warning(f"No current price available for {ticker_upper}. Serving cached prediction as-is.")
            return prediction

        current_price = float(indicators.price)
        prediction.preco_atual = Decimal(round(current_price, 2))

        if vp_per_share > 0:
            prediction.pvp_atual = Decimal(round(current_price / vp_per_share, 2))

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
        vp_per_share: float,
    ) -> None:
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "vp_per_share": vp_per_share,
            "prediction": prediction.model_dump(mode="json"),
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