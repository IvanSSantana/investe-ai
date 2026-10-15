import logging
from decimal import Decimal

from communication.dtos import QuantitativeValuationResult

logger = logging.getLogger(__name__)

class ValuationCalculator:
    """Calculates deterministic financial metrics for FII valuation anchoring."""

    def __init__(self, equity_risk_premium: Decimal = Decimal("0.025")):
        self._equity_risk_premium = equity_risk_premium

    def calculate(
        self,
        current_price: Decimal,
        vp_per_share: Decimal,
        historical_mean_pvp: Decimal,
        recent_dpus: list[Decimal],
        risk_free_rate: Decimal,
    ) -> QuantitativeValuationResult:
        """Computes DDM Fair Price, P/VP Mean Reversion, Yield Spread, the resulting
        fair price range [min, max], and upside/downside vs. current price —
        all deterministically, using a dynamic discount rate."""
        discount_rate = risk_free_rate + self._equity_risk_premium
        logger.info(f"Computing quantitative valuation with dynamic discount rate: {round(discount_rate * 100, 2)}%")

        if not recent_dpus:
            avg_monthly_dpu = Decimal("0")
        else:
            avg_monthly_dpu = Decimal(str(sum(recent_dpus) / len(recent_dpus)))

        annualized_dpu = avg_monthly_dpu * 12

        ddm_fair_price = annualized_dpu / discount_rate if discount_rate > 0 else Decimal("0")

        pvp_mean_reversion_price = vp_per_share * historical_mean_pvp

        current_annual_yield = (annualized_dpu / current_price) if current_price > 0 else Decimal("0")
        yield_spread_percent = (current_annual_yield - discount_rate) * 100

        preco_justo_min = min(ddm_fair_price, pvp_mean_reversion_price)
        preco_justo_max = max(ddm_fair_price, pvp_mean_reversion_price)

        fair_mid_price = (preco_justo_min + preco_justo_max) / 2
        upside_downside_percent = (
            ((fair_mid_price - current_price) / current_price) * 100 if current_price > 0 else Decimal("0")
        )

        return QuantitativeValuationResult(
            ddm_fair_price=round(ddm_fair_price, 2),
            pvp_mean_reversion_price=round(pvp_mean_reversion_price, 2),
            annualized_dpu=round(annualized_dpu, 2),
            yield_spread_percent=round(yield_spread_percent, 2),
            preco_justo_min=round(preco_justo_min, 2),
            preco_justo_max=round(preco_justo_max, 2),
            upside_downside_percent=round(upside_downside_percent, 2),
        )