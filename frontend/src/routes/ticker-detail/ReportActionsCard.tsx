import { useState, type SubmitEvent } from "react";
import { Card } from "../../components/ui/Card";
import { useDownloadReport, useSendReportEmail } from "../../queries/useFii";
import { errorMessage } from "../../helpers/errors";

export function ReportActionsCard({ ticker }: { ticker: string }) {
  const downloadMutation = useDownloadReport();
  const emailMutation = useSendReportEmail();
  const [email, setEmail] = useState("");

  const handleSend = (e: SubmitEvent) => {
    e.preventDefault();
    emailMutation.mutate(
      { ticker, email_to: email },
      { onSuccess: () => setEmail("") },
    );
  };

  return (
    <Card title="Relatório">
      <div style={{ marginBottom: 16 }}>
        <button
          type="button"
          onClick={() => downloadMutation.mutate(ticker)}
          disabled={downloadMutation.isPending}
        >
          {downloadMutation.isPending ? "Gerando relatório…" : "Baixar relatório (Markdown)"}
        </button>
        {downloadMutation.isError && (
          <p style={{ color: "crimson", marginTop: 8 }}>
            {errorMessage(downloadMutation.error, "Falha ao gerar o relatório.")}
          </p>
        )}
      </div>

      <form
        onSubmit={handleSend}
        style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}
      >
        <input
          type="email"
          placeholder="E-mail de destino"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          style={{ flex: "1 1 240px", padding: 8 }}
        />
        <button type="submit" disabled={emailMutation.isPending}>
          {emailMutation.isPending ? "Enviando…" : "Enviar por e-mail"}
        </button>
      </form>

      {emailMutation.isError && (
        <p style={{ color: "crimson", marginTop: 8 }}>
          {errorMessage(emailMutation.error, "Falha ao enviar o e-mail.")}
        </p>
      )}
      {emailMutation.isSuccess && (
        <p style={{ color: "#065f46", marginTop: 8 }}>{emailMutation.data.message}</p>
      )}
    </Card>
  );
}