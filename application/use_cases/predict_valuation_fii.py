import logging

from application.use_cases.get_indicators_fii import GetIndicatorsFiiUseCase
from communication.dtos import RealStateFundResponse, ValuationPredictionResponse
from domain.ai.ai_service import AiService
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
    ):
        self._ai_service = ai_service
        self._get_indicators_use_case = get_indicators_use_case
        self._yfinance_service = yfinance_service
        self._market_data_service = market_data_service

    def execute(self, ticker: str) -> ValuationPredictionResponse:
        """Fetches dynamic indicators, historical series, risk-free rate, and executes valuation pipeline."""
        ticker_upper = ticker.upper()
        logger.info(f"Executing Integrated Valuation Prediction Use Case for {ticker_upper}")

        raw_indicators = self._get_indicators_use_case.execute(ticker_upper)

        if isinstance(raw_indicators, dict):
            indicators = RealStateFundResponse(**raw_indicators)
        else:
            indicators = raw_indicators

        current_price = float(indicators.price) if indicators.price is not None else 0.0
        vp_per_share = float(indicators.asset_value)
    
        pvp = round(current_price / vp_per_share, 2) 

        history = self._yfinance_service.get_price_history(f"{ticker_upper}.SA")

        recent_dpus: list[float] = []
        if not history.empty and "Dividends" in history.columns:
            dividends = history["Dividends"][history["Dividends"] > 0]
            if not dividends.empty:
                recent_dpus = [float(val) for val in dividends.tail(3).tolist()]

        if not recent_dpus:
            logger.warning(
                f"No dividend history found for {ticker_upper}. Estimating DPU from current price and dividend yield."
            )
            annual_dy_percent = float(indicators.dividend_yield)
            
            estimated_monthly_dpu = (current_price * (annual_dy_percent / 100.0)) / 12.0
            recent_dpus = [estimated_monthly_dpu] 

        risk_free_rate = self._market_data_service.get_current_risk_free_rate()

        return self._ai_service.predict_valuation(
            ticker=ticker_upper,
            current_price=current_price,
            vp_per_share=vp_per_share,
            pvp=pvp,
            recent_dpus=recent_dpus,
            risk_free_rate=risk_free_rate,
        )