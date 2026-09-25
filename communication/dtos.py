from pydantic import BaseModel, EmailStr, Field
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
    dividend_yield_segment_average: Decimal | None = None
    liquidity: Decimal | None = None
    vacancy_rate: Decimal | None = None
    asset_value: Decimal | None = None
    fees: Decimal | None = None

class SendReportEmailRequest(BaseModel):
    ticker: str = Field(..., example="HGLG11", description="FII Ticker symbol")
    email_to: EmailStr = Field(..., example="user@example.com", description="Recipient email address")

class ScheduleReportRequest(BaseModel):
    ticker: str = Field(..., example="HGLG11")
    email_to: EmailStr = Field(..., example="user@example.com")
    day_of_month: int = Field(default=1, ge=1, le=28, description="Day of the month to trigger the email")
    hour: int = Field(default=9, ge=0, le=23, description="Hour of the day (0-23)")