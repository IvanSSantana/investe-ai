from pydantic import BaseModel
from decimal import Decimal

class StockResponse(BaseModel):
    ticker: str
    price: Decimal | None
    value_variation_1y: Decimal | None
    value_variation_1m: Decimal | None
    pl: Decimal | None
    pvp: Decimal | None
    dividend_yield: Decimal | None
    roe: Decimal | None = None
    roic: Decimal | None = None
    net_debt_to_EBITDA: Decimal | None = None  # Dívida Líquida / EBITDA
    ev_to_EBITDA: Decimal | None = None
    profit_cagr: Decimal | None = None
    payout: Decimal | None = None
    net_margin: Decimal | None = None  # Margem Líquida
    ebit_margin: Decimal | None = None
    segment: str | None = None

class RealStateFundResponse(BaseModel):
    ticker: str | None = None
    segment: str | None = None
    type_fund: str | None = None
    management_style: str | None = None
    unitholders: Decimal | None = None
    price: Decimal | None = None
    value_variation_1m: Decimal | None = None
    value_variation_1y: Decimal | None = None
    dividend_yield: Decimal | None = None
    liquidity: Decimal | None = None
    vacancy_rate: Decimal | None = None
    asset_value: Decimal | None = None
    fees: Decimal | None = None