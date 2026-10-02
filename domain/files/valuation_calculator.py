import logging
from dataclasses import dataclass

from communication.dtos import QuantitativeValuationResult

logger = logging.getLogger(__name__)

class ValuationCalculator:
    """Calculates deterministic financial metrics for FII valuation anchoring."""

    def __init__(self, equity_risk_premium: float = 0.025):
        self._equity_risk_premium = equity_risk_premium

    def calculate(
        self,
        current_price: float,
        vp_per_share: float,
        historical_mean_pvp: float,
        recent_dpus: list[float],
        risk_free_rate: float,
    ) -> QuantitativeValuationResult:
        """Computes DDM Fair Price, P/VP Mean Reversion, and Yield Spread using a dynamic discount rate."""
        discount_rate = risk_free_rate + self._equity_risk_premium
        logger.info(f"Computing quantitative valuation with dynamic discount rate: {round(discount_rate * 100, 2)}%")

        if not recent_dpus:
            avg_monthly_dpu = 0.0
        else:
            avg_monthly_dpu = sum(recent_dpus) / len(recent_dpus)

        annualized_dpu = avg_monthly_dpu * 12

        ddm_fair_price = annualized_dpu / discount_rate if discount_rate > 0 else 0.0

        pvp_mean_reversion_price = vp_per_share * historical_mean_pvp

        current_annual_yield = (annualized_dpu / current_price) if current_price > 0 else 0.0
        yield_spread_percent = (current_annual_yield - discount_rate) * 100

        return QuantitativeValuationResult(
            ddm_fair_price=round(ddm_fair_price, 2),
            pvp_mean_reversion_price=round(pvp_mean_reversion_price, 2),
            annualized_dpu=round(annualized_dpu, 2),
            yield_spread_percent=round(yield_spread_percent, 2),
        )