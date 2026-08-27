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
    ticker: str
    price: Decimal
    value_variation: Decimal
    dividend_yield: Decimal
    segment: str
    liquidity: Decimal
    profitability: Decimal
    unitholders: int
    vacancy_rate: Decimal
    asset_value: Decimal
    fees: Decimal