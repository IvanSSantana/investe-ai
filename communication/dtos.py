from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator
from decimal import Decimal, InvalidOperation

def _sanitize_decimal_fields(*field_names: str):
    """Returns a Pydantic 'before' validator that sanitizes string-typed numeric
    values (ex.: 'R$ 1.234,56', '12,5%') using price_sanitizer before type coercion."""
    @field_validator(*field_names, mode="before")
    @classmethod
    def _sanitize(cls, value):
        if isinstance(value, str):
            cleaned = value.replace("R$", "").replace("%", "").strip()
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                return value
        return value

    return _sanitize

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
    pvp: Decimal | None = None
    vp_per_share: Decimal | None = None
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
    estimativa_proximo_rendimento: Decimal = Field(
        ..., description="Projeção do próximo dividendo por cota em R$"
    )
    yield_mensal_estimado_percent: Decimal = Field(
        ..., description="Dividend Yield mensal projetado em %"
    )
    tendencia_30d: str = Field(
        ..., description="Tendência para os próximos 30 dias: 'Alta', 'Neutra' ou 'Baixa'"
    )
    gatilhos_imediatos: list[str] = Field(
        ..., description="Fatos do relatório ou notícias com impacto no curto prazo"
    )

    _sanitize_values = _sanitize_decimal_fields("estimativa_proximo_rendimento", "yield_mensal_estimado_percent")

class MediumTermValuation(BaseModel):
    preco_justo_min: Decimal = Field(
        ..., description="Limite inferior da faixa de preço justo de 12M em R$"
    )
    preco_justo_max: Decimal = Field(
        ..., description="Limite superior da faixa de preço justo de 12M em R$"
    )
    upside_downside_percent: Decimal = Field(
        ..., description="Potencial de valorização/desvalorização sobre o preço atual em %"
    )
    tendencia_12m: str = Field(
        ..., description="Tendência estrutural para 12 meses: 'Alta', 'Neutra' ou 'Baixa'"
    )
    tese_investimento: str = Field(
        ..., description="Síntese da tese cruzando Valuation, DRE e contexto de mercado"
    )

    _sanitize_values = _sanitize_decimal_fields("preco_justo_min", "preco_justo_max", "upside_downside_percent")

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

    _sanitize_values = _sanitize_decimal_fields("preco_atual", "pvp_atual")

class QuantitativeValuationResult(BaseModel):
    ddm_fair_price: Decimal
    pvp_mean_reversion_price: Decimal
    annualized_dpu: Decimal
    yield_spread_percent: Decimal
    preco_justo_min: Decimal
    preco_justo_max: Decimal
    upside_downside_percent: Decimal

    _sanitize_values = _sanitize_decimal_fields(
        "ddm_fair_price", "pvp_mean_reversion_price", "annualized_dpu", "yield_spread_percent",
        "preco_justo_min", "preco_justo_max", "upside_downside_percent"
    )

class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., description="Rótulo humano para identificar a finalidade da chave")
    expires_at: datetime | None = Field(None, description="Data de expiração opcional da chave")
 
class ApiKeyCreateResponse(BaseModel):
    key_id: str
    api_key: str = Field(..., description="Chave em texto plano — exibida apenas nesta resposta")
    name: str
    created_at: datetime
    expires_at: datetime | None