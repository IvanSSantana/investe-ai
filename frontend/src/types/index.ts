export interface UserResponse {
  user_id: string;
  email: string;
  created_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface ApiKeyCreateRequest {
  name: string;
  expires_at: string | null;
}

export interface ApiKeyCreateResponse {
  key_id: string;
  api_key: string;
  name: string;
  created_at: string;
  expires_at: string | null;
}

export interface RealStateFundResponse {
  ticker: string | null;
  segment: string | null;
  type_fund: string | null;
  management_style: string | null;
  unitholders: number | null;
  price: number | null;
  pvp: number | null;
  vp_per_share: number | null;
  value_variation_1m: number | null;
  value_variation_1y: number | null;
  dividend_yield: number | null;
  dividend_yield_segment_average: number | null;
  liquidity: number | null;
  vacancy_rate: number | null;
  asset_value: number | null;
  fees: number | null;
}

export interface SendReportEmailRequest {
  ticker: string;
  email_to: string;
}

export interface ScheduleReportRequest {
  ticker: string;
  email_to: string;
  day_of_month: number;
  hour: number;
}

export type Trend = "Alta" | "Neutra" | "Baixa";
export type Recommendation =
  | "Compra Forte"
  | "Compra"
  | "Aguardar/Neutro"
  | "Venda";

export interface ShortTermProjection {
  estimativa_proximo_rendimento: number;
  yield_mensal_estimado_percent: number;
  tendencia_30d: Trend;
  gatilhos_imediatos: string[];
}

export interface MediumTermValuation {
  preco_justo_min: number;
  preco_justo_max: number;
  upside_downside_percent: number;
  tendencia_12m: Trend;
  tese_investimento: string;
}

export interface ValuationPredictionResponse {
  ticker: string;
  preco_atual: number;
  pvp_atual: number;
  curto_prazo: ShortTermProjection;
  medio_prazo: MediumTermValuation;
  sinal_recomendacao: Recommendation;
  riscos_monitorados: string[];
}