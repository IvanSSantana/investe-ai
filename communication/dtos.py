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
    ticker: str = Field(..., example="HGLG11", description="FII Ticker symbol") # type: ignore
    email_to: EmailStr = Field(..., example="user@example.com", description="Recipient email address") # type: ignore

class ScheduleReportRequest(BaseModel):
    ticker: str = Field(..., example="HGLG11") # type: ignore
    email_to: EmailStr = Field(..., example="user@example.com") # type: ignore
    day_of_month: int = Field(default=1, ge=1, le=31, description="Day of the month to trigger the email")
    hour: int = Field(default=9, ge=0, le=23, description="Hour of the day (0-23)")

class ShortTermProjection(BaseModel):
    estimativa_proximo_rendimento: float = Field(
        ..., description="Projeção do próximo dividendo por cota em R$"
    )
    yield_mensal_estimado_percent: float = Field(
        ..., description="Dividend Yield mensal projetado em %"
    )
    tendencia_30d: str = Field(
        ..., description="Tendência para os próximos 30 dias: 'Alta', 'Neutra' ou 'Baixa'"
    )
    gatilhos_imediatos: list[str] = Field(
        ..., description="Fatos do relatório ou notícias com impacto no curto prazo"
    )

class MediumTermValuation(BaseModel):
    preco_justo_min: float = Field(
        ..., description="Limite inferior da faixa de preço justo de 12M em R$"
    )
    preco_justo_max: float = Field(
        ..., description="Limite superior da faixa de preço justo de 12M em R$"
    )
    upside_downside_percent: float = Field(
        ..., description="Potencial de valorização/desvalorização sobre o preço atual em %"
    )
    tendencia_12m: str = Field(
        ..., description="Tendência estrutural para 12 meses: 'Alta', 'Neutra' ou 'Baixa'"
    )
    tese_investimento: str = Field(
        ..., description="Síntese da tese cruzando Valuation, DRE e contexto de mercado"
    )

class ValuationPredictionResponse(BaseModel):
    ticker: str
    preco_atual: Decimal
    pvp_atual: Decimal
    curto_prazo: ShortTermProjection
    medio_prazo: MediumTermValuation
    sinal_recomendacao: str = Field(
        ..., description="Sinal consolidado: 'Compra Forte', 'Compra', 'Aguardar/Neutro' ou 'Venda'"
    )
    riscos_monitorados: list[str] = Field(
        ..., description="Principais riscos mapeados nos relatórios e notícias"
    )

class QuantitativeValuationResult(BaseModel):
    ddm_fair_price: Decimal
    pvp_mean_reversion_price: Decimal
    annualized_dpu: Decimal
    yield_spread_percent: Decimal