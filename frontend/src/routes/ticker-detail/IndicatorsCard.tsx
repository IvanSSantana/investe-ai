import { Card } from "../../components/ui/Card";
import { useIndicators } from "../../queries/useFii";
import { errorMessage } from "../../helpers/errors";
import { fmtBRL, fmtNum, fmtPct } from "../../helpers/formatters";
import type { RealStateFundResponse } from "../../types";

export function IndicatorsCard({ ticker }: { ticker: string }) {
  const { data, isLoading, isError, error } = useIndicators(ticker);

  return (
    <Card title="Indicadores">
      {isLoading && <p>Carregando indicadores…</p>}
      {isError && (
        <p style={{ color: "crimson", margin: 0 }}>
          {errorMessage(error, "Não foi possível carregar os indicadores.")}
        </p>
      )}
      {data && <IndicatorsGrid fund={data} />}
    </Card>
  );
}

function IndicatorsGrid({ fund }: { fund: RealStateFundResponse }) {
  const rows: { label: string; value: string }[] = [
    { label: "Preço da cota", value: fmtBRL(fund.price) },
    { label: "P/VP", value: fmtNum(fund.pvp) },
    { label: "Dividend Yield", value: fmtPct(fund.dividend_yield) },
    { label: "DY (média do segmento)", value: fmtPct(fund.dividend_yield_segment_average) },
    { label: "Variação 1 mês", value: fmtPct(fund.value_variation_1m) },
    { label: "Variação 12 meses", value: fmtPct(fund.value_variation_1y) },
    { label: "Vacância", value: fmtPct(fund.vacancy_rate) },
    { label: "Liquidez diária", value: fmtBRL(fund.liquidity) },
    { label: "Valor patrimonial", value: fmtBRL(fund.asset_value) },
    { label: "VP por cota", value: fmtBRL(fund.vp_per_share) },
    { label: "Taxa de administração", value: fmtPct(fund.fees) },
    {
      label: "Cotistas",
      value: fund.unitholders === null ? "—" : Number(fund.unitholders).toLocaleString("pt-BR"),
    },
    { label: "Segmento", value: fund.segment ?? "—" },
    { label: "Tipo de fundo", value: fund.type_fund ?? "—" },
    { label: "Gestão", value: fund.management_style ?? "—" },
  ];

  return (
    <dl
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))",
        gap: 12,
        margin: 0,
      }}
    >
      {rows.map((row) => (
        <div key={row.label}>
          <dt style={{ fontSize: 12, color: "#6b7280" }}>{row.label}</dt>
          <dd style={{ margin: 0, fontSize: 16, fontWeight: 600 }}>{row.value}</dd>
        </div>
      ))}
    </dl>
  );
}