import { Link, useParams } from "react-router-dom";
import { IndicatorsCard } from "./IndicatorsCard";
import { ValuationCard } from "./ValuationCard";
import { ReportActionsCard } from "./ReportActionsCard";
import { ScheduleCard } from "./ScheduleCard";

export default function TickerDetail() {
  const { ticker } = useParams<{ ticker: string }>();

  if (!ticker) {
    return <div style={{ padding: 24 }}>Ticker inválido.</div>;
  }

  return (
    <div style={{ maxWidth: 960, margin: "0 auto", padding: 24 }}>
      <header style={{ marginBottom: 24 }}>
        <Link to="/dashboard">← Voltar</Link>
        <h1 style={{ margin: "8px 0 0" }}>{ticker.toUpperCase()}</h1>
      </header>

      <IndicatorsCard ticker={ticker} />
      <ValuationCard ticker={ticker} />
      <ReportActionsCard ticker={ticker} />
      <ScheduleCard ticker={ticker} />
    </div>
  );
}