import { Badge, type BadgeVariant } from "../../components/ui/Badge";
import { Card } from "../../components/ui/Card";
import { useValuation } from "../../queries/useFii";
import { errorMessage } from "../../helpers/errors";
import { fmtBRL, fmtNum, fmtPct } from "../../helpers/formatters";
import type {
  MediumTermValuation,
  Recommendation,
  ShortTermProjection,
  Trend,
  ValuationPredictionResponse,
} from "../../types";

const recommendationVariant: Record<Recommendation, BadgeVariant> = {
  "Compra Forte": "success",
  Compra: "info",
  "Aguardar/Neutro": "warning",
  Venda: "danger",
};

const trendVariant: Record<Trend, BadgeVariant> = {
  Alta: "success",
  Neutra: "neutral",
  Baixa: "danger",
};

export function ValuationCard({ ticker }: { ticker: string }) {
  const { data, isLoading, isError, error } = useValuation(ticker);

  return (
    <Card title="Valuation">
      {isLoading && <p>Analisando valuation (pode levar alguns segundos)…</p>}
      {isError && (
        <p style={{ color: "crimson", margin: 0 }}>
          {errorMessage(error, "Não foi possível calcular o valuation.")}
        </p>
      )}
      {data && <ValuationContent data={data} />}
    </Card>
  );
}

function ValuationContent({ data }: { data: ValuationPredictionResponse }) {
  return (
    <>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          marginBottom: 16,
          flexWrap: "wrap",
        }}
      >
        <Badge variant={recommendationVariant[data.sinal_recomendacao]} size="md">
          {data.sinal_recomendacao}
        </Badge>
        <span style={{ color: "#6b7280", fontSize: 14 }}>
          Preço atual: {fmtBRL(data.preco_atual)} · P/VP: {fmtNum(data.pvp_atual)}
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <ShortTermBlock data={data.curto_prazo} />
        <MediumTermBlock data={data.medio_prazo} />
      </div>

      {data.riscos_monitorados.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h4 style={{ margin: "0 0 8px" }}>Riscos monitorados</h4>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            {data.riscos_monitorados.map((risk, i) => (
              <li key={i}>{risk}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}

function ShortTermBlock({ data }: { data: ShortTermProjection }) {
  return (
    <div>
      <h3 style={{ margin: "0 0 8px", fontSize: 16, display: "flex", alignItems: "center", gap: 8 }}>
        Curto prazo
        <Badge variant={trendVariant[data.tendencia_30d]}>{data.tendencia_30d}</Badge>
      </h3>
      <p style={{ margin: "4px 0" }}>
        <strong>Próximo rendimento estimado:</strong> {fmtBRL(data.estimativa_proximo_rendimento)}
      </p>
      <p style={{ margin: "4px 0" }}>
        <strong>Yield mensal estimado:</strong> {fmtPct(data.yield_mensal_estimado_percent)}
      </p>
      {data.gatilhos_imediatos.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <strong style={{ fontSize: 14 }}>Gatilhos imediatos</strong>
          <ul style={{ margin: "4px 0 0", paddingLeft: 20 }}>
            {data.gatilhos_imediatos.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function MediumTermBlock({ data }: { data: MediumTermValuation }) {
  return (
    <div>
      <h3 style={{ margin: "0 0 8px", fontSize: 16, display: "flex", alignItems: "center", gap: 8 }}>
        Médio prazo (12 meses)
        <Badge variant={trendVariant[data.tendencia_12m]}>{data.tendencia_12m}</Badge>
      </h3>
      <p style={{ margin: "4px 0" }}>
        <strong>Faixa de preço justo:</strong> {fmtBRL(data.preco_justo_min)} –{" "}
        {fmtBRL(data.preco_justo_max)}
      </p>
      <p style={{ margin: "4px 0" }}>
        <strong>Upside/Downside:</strong>{" "}
        <span
          style={{
            color: data.upside_downside_percent >= 0 ? "#065f46" : "#991b1b",
            fontWeight: 600,
          }}
        >
          {fmtPct(data.upside_downside_percent)}
        </span>
      </p>
      <p style={{ margin: "8px 0 0", fontSize: 14, color: "#374151" }}>
        {data.tese_investimento}
      </p>
    </div>
  );
}